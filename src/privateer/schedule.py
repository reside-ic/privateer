import os
import shutil
import tempfile
from typing import List

import docker
from fabric import Connection
from invoke import UnexpectedExit

from privateer.config import PrivateerHost, PrivateerTarget
from privateer.docker_helpers import DockerClient


def generate_config(target: PrivateerTarget):
    for s in target.schedules:
        with open(f"offen/{target.name}-{s.name}.conf", "w") as f:
            f.write(f"BACKUP_FILENAME={target.name}-{s.name}-%Y-%m-%dT%H-%M-%S.tar.gz")
            f.write(f"BACKUP_PRUNING_PREFIX={target.name}-{s.name}-")
            if s.retention_days is not None:
                f.write(f"BACKUP_RETENTION_DAYS={s.retention_days}")


def get_offen_env(host: PrivateerHost):
    if host.host_type == "local":
        return {"SSH_HOST_NAME": host.hostname,
                "SSH_REMOTE_PATH": host.path,
                "SSH_USER": host.user
                }


def backup(host: PrivateerHost, targets: List[PrivateerTarget]):
    env = get_offen_env(host);
    if host.host_type == "local":
        # schedule backup
        env = {"SSH_HOST_NAME": host.hostname,
               "SSH_REMOTE_PATH": host.path,
               "SSH_USER": host.user
               }
        pass
    else:
        check_host_path(host)
        mounts = [docker.types.Mount("/root/.ssh", "/home/aehill/.ssh",
                                     type="bind")]
        for t in targets:
            mounts.append(docker.types.Mount(f"/backup/{t.name}", t.name))
        with DockerClient() as cl:
            cl.containers.run(
                "offen/docker-volume-backup:v2",
                mounts=mounts,
                environment={"SSH_HOST_NAME": host.hostname,
                             "SSH_REMOTE_PATH": host.path,
                             "SSH_USER": host.user
                             }
            )
    return True


def restore(host: PrivateerHost, targets: List[PrivateerTarget]):
    success = []
    if host.host_type == "local":
        for t in targets:
            path = os.path.join(host.path, f"{t.name}.tar")
            if not os.path.exists(path):
                msg = f"Backup path '{path}' does not exist. Not restoring {t.name}"
                print(msg)
            else:
                untar_volume(t, host.path)
                success.append(t.name)
                print(f"Restored {path} to {t.name}")
    else:
        with Connection(host=host.hostname, user=host.user,
                        port=host.port) as c:
            with tempfile.TemporaryDirectory() as local_backup_path:
                for t in targets:
                    remote_path = os.path.join(host.path, f"{t.name}.tar")
                    try:
                        c.run(f"test -f {remote_path}", in_stream=False)
                        c.get(remote_path, f"{local_backup_path}/")
                        untar_volume(t, local_backup_path)
                        success.append(t.name)
                        print(f"Restored {remote_path} to {t.name}")
                    except UnexpectedExit:
                        msg = f"Backup path '{remote_path}' does not exist. Not restoring {t.name}"
                        print(msg)
    return success


def check_host_path(host: PrivateerHost):
    with Connection(host=host.hostname, user=host.user,
                    port=host.port) as c:
        try:
            c.run(f"test -d {host.path}", in_stream=False)
        except UnexpectedExit as err:
            msg = f"Host path '{host.path}' does not exist. Either make directory or fix config."
            raise Exception(msg) from err


def tar_volume(target: PrivateerTarget):
    tmp = tempfile.gettempdir()
    local_backup_path = os.path.join(tmp, "backup")
    if not os.path.exists(local_backup_path):
        os.mkdir(local_backup_path)
    volume_mount = docker.types.Mount("/data", target.name)
    backup_mount = docker.types.Mount("/backup", local_backup_path, type="bind")
    with DockerClient() as cl:
        cl.containers.run(
            "ubuntu",
            remove=True,
            mounts=[volume_mount, backup_mount],
            command=["tar", "cvf", f"/backup/{target.name}.tar", "-C", "/data",
                     "."],
        )
    return f"{local_backup_path}/{target.name}.tar"


def untar_volume(target: PrivateerTarget, backup_path):
    volume_mount = docker.types.Mount("/data", target.name)
    backup_mount = docker.types.Mount("/backup", backup_path, type="bind")
    with DockerClient() as cl:
        cl.containers.run(
            "ubuntu",
            remove=True,
            mounts=[volume_mount, backup_mount],
            command=["tar", "xvf", f"/backup/{target.name}.tar", "-C", "/data"],
        )
    return True
