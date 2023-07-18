import json
import os
from typing import List

import docker
from fabric import Connection
from invoke import UnexpectedExit

from privateer.config import PrivateerHost, PrivateerTarget
from privateer.docker_helpers import DockerClient, containers_matching
from privateer.docker_helpers import string_into_container, string_from_container

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
OFFEN_DIR = os.path.join(ROOT_DIR, "offen")


def get_mounts(host):
    mounts = [
        docker.types.Mount("/etc/timezone", "/etc/timezone", type="bind"),
        docker.types.Mount("/etc/localtime", "/etc/localtime", type="bind"),
    ]
    if host.host_type == "remote":
        mounts.append(
            docker.types.Mount("/root/.ssh", os.path.expanduser("~/.ssh"),
                               type="bind"))
    else:
        mounts.append(docker.types.Mount("/archive", host.path, type="bind"))
    return mounts


def get_env(host):
    if host.host_type == "remote":
        env = {"SSH_HOST_NAME": host.hostname, "SSH_REMOTE_PATH": host.path,
               "SSH_USER": host.user}
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
                environment={**env, "BACKUP_FILENAME": filename,
                             "BACKUP_SOURCES": f"/{t.name}"},
                remove=True,
                entrypoint=["backup"],
            )
    return True


def generate_backup_config(target: PrivateerTarget, conf_path):
    if len(target.schedules) == 0:
        msg = f"No backup schedules defined for target {target.name}"
        raise Exception(msg)
    if not os.path.exists(conf_path):
        os.makedirs(conf_path)
    filenames = []
    for s in target.schedules:
        filename = f"{conf_path}/{target.name}-{s.name}.conf"
        filenames.append(filename)
        with open(filename, "w") as f:
            f.write(f'BACKUP_SOURCES="/backup/{target.name}"\n')
            f.write(
                f'BACKUP_FILENAME="{target.name}-{s.name}-%Y-%m-%dT%H-%M-%S.tar.gz"\n')
            f.write(f'BACKUP_PRUNING_PREFIX="{target.name}-{s.name}-"\n')
            f.write(f'BACKUP_CRON_EXPRESSION="{s.schedule}"\n')
            if s.retention_days is not None:
                f.write(f'BACKUP_RETENTION_DAYS="{s.retention_days}"\n')
    return filenames


def schedule_backups(host: PrivateerHost, targets: List[PrivateerTarget]):
    check_host_path(host)
    mounts = get_mounts(host)
    env = get_env(host)
    offen_conf_path = os.path.join(os.path.abspath(OFFEN_DIR), host.name)
    for t in targets:
        mounts.append(docker.types.Mount(f"/backup/{t.name}", t.name))
        generate_backup_config(t, offen_conf_path)
    mounts.append(
        docker.types.Mount("/etc/dockervolumebackup/conf.d", offen_conf_path,
                           type="bind"))
    name = f"privateer_{host.name}"
    with DockerClient() as cl:
        container = cl.containers.run(
            "offen/docker-volume-backup:v2", name=name, mounts=mounts,
            environment=env, detach=True
        )
        string_into_container(json.dumps({"host": host, "targets": targets}),
                              container,
                              "/etc/dockervolumebackup/config.json")
        if container.status in ["running", "created"]:
            return True
        else:
            return container.logs().decode("UTF-8")


def list_scheduled_backups():
    running = containers_matching("privateer")
    if len(running) == 0:
        return []
    else:
        return [json.loads(string_from_container(container,
                                                 "/etc/dockervolumebackup/config.json"))
                for
                container in running]


def get_host_conf_path(name):
    return os.path.join(OFFEN_DIR, name)


def cancel_scheduled_backups(host):
    if host is not None:
        running = containers_matching(f"privateer_{host}")
    else:
        running = containers_matching("privateer")
    names = [r.name for r in running]
    [r.stop() for r in running]
    [r.remove() for r in running]
    return names


def check_host_path(host: PrivateerHost):
    if host.host_type == "local":
        if not os.path.exists(host.path):
            msg = f"Host path '{host.path}' does not exist. Either make directory or fix config."
            raise Exception(msg)
    else:
        with Connection(host=host.hostname, user=host.user,
                        port=host.port) as c:
            try:
                c.run(f"test -d {host.path}", in_stream=False)
            except UnexpectedExit as err:
                msg = f"Host path '{host.path}' does not exist. Either make directory or fix config."
                raise Exception(msg) from err
