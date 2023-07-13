import os
import random
import string
from typing import List

import docker
from fabric import Connection
from invoke import UnexpectedExit

from privateer.config import PrivateerHost, PrivateerTarget
from privateer.docker_helpers import DockerClient, containers_matching


def get_mounts(host):
    mounts = [
        docker.types.Mount("/etc/timezone", "/etc/timezone", type="bind"),
        docker.types.Mount("/etc/localtime", "/etc/localtime", type="bind"),
    ]
    if host.host_type == "remote":
        mounts.append(docker.types.Mount("/root/.ssh", os.path.expanduser("~/.ssh"), type="bind"))
    else:
        mounts.append(docker.types.Mount("/archive", host.path, type="bind"))
    return mounts


def get_env(host):
    if host.host_type == "remote":
        env = {"SSH_HOST_NAME": host.hostname, "SSH_REMOTE_PATH": host.path, "SSH_USER": host.user}
    else:
        env = {}
    return env


def backup(host: PrivateerHost, targets: List[PrivateerTarget]):
    check_host_path(host)
    mounts = get_mounts(host)
    env = get_env(host)

    for t in targets:
        mounts.append(docker.types.Mount(f"/{t.name}", t.name))
        filename = f"{t.name}-%Y-%m-%dT%H-%M-%S.tar.gz"
        with DockerClient() as cl:
            cl.containers.run(
                "offen/docker-volume-backup:v2",
                mounts=mounts,
                environment={**env, "BACKUP_FILENAME": filename, "BACKUP_SOURCES": f"/{t.name}"},
                remove=True,
                entrypoint=["backup"],
            )
    return True


def generate_backup_config(target: PrivateerTarget):
    if len(target.schedules) == 0:
        msg = f"No backup schedules defined for target {target.name}"
        raise Exception(msg)
    if not os.path.exists("offen"):
        os.mkdir("offen")
    filenames = []
    for s in target.schedules:
        filename = f"offen/{target.name}-{s.name}.conf"
        filenames.append(filename)
        with open(filename, "w") as f:
            f.write(f'BACKUP_SOURCES="/backup/{target.name}"\n')
            f.write(f'BACKUP_FILENAME="{target.name}-{s.name}-%Y-%m-%dT%H-%M-%S.tar.gz"\n')
            f.write(f'BACKUP_PRUNING_PREFIX="{target.name}-{s.name}-"\n')
            f.write(f'BACKUP_CRON_EXPRESSION="{s.schedule}"\n')
            if s.retention_days is not None:
                f.write(f'BACKUP_RETENTION_DAYS="{s.retention_days}"\n')
    return filenames


def schedule_backups(host: PrivateerHost, targets: List[PrivateerTarget]):
    check_host_path(host)
    mounts = get_mounts(host)
    env = get_env(host)
    for t in targets:
        mounts.append(docker.types.Mount(f"/backup/{t.name}", t.name))
        generate_backup_config(t)
    path = os.path.abspath("offen")
    mounts.append(docker.types.Mount("/etc/dockervolumebackup/conf.d", path, type="bind"))
    name = f"privateer_{''.join(random.choices(string.ascii_letters, k=6))}"  # noqa: S311
    with DockerClient() as cl:
        cl.containers.run(
            "offen/docker-volume-backup:v2", name=name, mounts=mounts, environment=env, detach=True, remove=True
        )
    return True


def cancel_scheduled_backups():
    running = containers_matching("privateer")
    [r.stop() for r in running]


def check_host_path(host: PrivateerHost):
    if host.host_type == "local":
        if not os.path.exists(host.path):
            msg = f"Host path '{host.path}' does not exist. Either make directory or fix config."
            raise Exception(msg)
    else:
        with Connection(host=host.hostname, user=host.user, port=host.port) as c:
            try:
                c.run(f"test -d {host.path}", in_stream=False)
            except UnexpectedExit as err:
                msg = f"Host path '{host.path}' does not exist. Either make directory or fix config."
                raise Exception(msg) from err
