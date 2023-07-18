import json
import os
from typing import List

import docker
from fabric import Connection
from invoke import UnexpectedExit

from privateer.config import PrivateerHost, PrivateerTarget
from privateer.docker_helpers import DockerClient, containers_matching, string_from_container, string_into_container

OFFEN_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "offen")
OFFEN_IMAGE = "offen/docker-volume-backup:v2"
DOCKER_OFFEN_CONFIG_PATH = "/etc/dockervolumebackup/config.json"


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
        filename = f"{backup_prefix(t, None)}-%Y-%m-%dT%H-%M-%S.tar.gz"
        with DockerClient() as cl:
            cl.containers.run(
                OFFEN_IMAGE,
                mounts=mounts,
                environment={**env, "BACKUP_FILENAME": filename, "BACKUP_SOURCES": f"/{t.name}"},
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
    for s in target.schedules:
        filename = f"{conf_path}/{target.name}-{s.name}.conf"
        prefix = backup_prefix(target, s)
        with open(filename, "w") as f:
            f.write(f'BACKUP_SOURCES="/backup/{target.name}"\n')
            f.write(f'BACKUP_FILENAME="{prefix}-%Y-%m-%dT%H-%M-%S.tar.gz"\n')
            f.write(f'BACKUP_PRUNING_PREFIX="{prefix}-"\n')
            f.write(f'BACKUP_CRON_EXPRESSION="{s.schedule}"\n')
            if s.retention_days is not None:
                f.write(f'BACKUP_RETENTION_DAYS="{s.retention_days}"\n')
    return True


def backup_prefix(t, s):
    machine_name = os.uname().nodename
    if s is not None:
        return f"{t.name}-{s.name}-{machine_name}"
    else:
        return f"{t.name}-{machine_name}"


def schedule_backups(host: PrivateerHost, targets: List[PrivateerTarget]):
    check_host_path(host)
    mounts = get_mounts(host)
    env = get_env(host)
    offen_conf_path = os.path.join(os.path.abspath(OFFEN_DIR), host.name)
    for t in targets:
        mounts.append(docker.types.Mount(f"/backup/{t.name}", t.name))
        generate_backup_config(t, offen_conf_path)
    mounts.append(docker.types.Mount("/etc/dockervolumebackup/conf.d", offen_conf_path, type="bind"))
    name = f"privateer_{host.name}"
    with DockerClient() as cl:
        container = cl.containers.run(OFFEN_IMAGE, name=name, mounts=mounts, environment=env, detach=True)
        record_config_in_container(host, targets, container)
        if container.status in ["running", "created"]:
            return True
        else:
            return container.logs().decode("UTF-8")


def record_config_in_container(host, targets, container):
    string_into_container(json.dumps({"host": host, "targets": targets}), container, DOCKER_OFFEN_CONFIG_PATH)


def list_scheduled_backups():
    running = containers_matching("privateer")
    if len(running) == 0:
        return []
    else:
        return [json.loads(string_from_container(container, DOCKER_OFFEN_CONFIG_PATH)) for container in running]


def get_host_conf_path(name):
    return os.path.join(OFFEN_DIR, name)


def cancel_scheduled_backups(host):
    if host is not None:
        running = containers_matching(f"privateer_{host}")
    else:
        running = containers_matching("privateer")
    names = [r.name.replace("privateer_", "") for r in running]
    [r.stop() for r in running]
    [r.remove() for r in running]
    return names


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
