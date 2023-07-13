import glob
import os
import tempfile
from typing import List

import docker
from fabric import Connection
from invoke import UnexpectedExit

from privateer.config import PrivateerHost, PrivateerTarget
from privateer.docker_helpers import DockerClient


def backup(host: PrivateerHost, targets: List[PrivateerTarget]):
    check_host_path(host)
    mounts = [
        docker.types.Mount("/etc/timezone", "/etc/timezone", type="bind"),
        docker.types.Mount("/etc/localtime", "/etc/localtime", type="bind"),
    ]
    if host.host_type == "remote":
        env = {"SSH_HOST_NAME": host.hostname, "SSH_REMOTE_PATH": host.path, "SSH_USER": host.user}
        mounts.append(docker.types.Mount("/root/.ssh", os.path.expanduser("~/.ssh"), type="bind"))
    else:
        mounts.append(docker.types.Mount("/archive", host.path, type="bind"))
        env = {}

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


def restore(host: PrivateerHost, targets: List[PrivateerTarget]):
    success = []
    if host.host_type == "local":
        for t in targets:
            path = get_most_recent_backup(host.path, t.name)
            if path is None:
                msg = f"No backups found. Not restoring {t.name}"
                print(msg)
            else:
                untar_volume(t, path)
                success.append(t.name)
                print(f"Restored {path} to {t.name}")
    else:
        with Connection(host=host.hostname, user=host.user, port=host.port) as c:
            with tempfile.TemporaryDirectory() as local_backup_path:
                for t in targets:
                    res = c.run(f"ls -t {host.path}/{t.name}-*.tar.gz | head -1", in_stream=False, pty=True)
                    if res.ok:
                        file = res.stdout.strip()
                        c.get(file, f"{local_backup_path}/")
                        untar_volume(t, f"{local_backup_path}/{os.path.basename(file)}")
                        success.append(t.name)
                        print(f"Restored {file} to {t.name}")
                    else:
                        msg = f"No backups found. Not restoring {t.name}"
                        print(msg)
    return success


def get_most_recent_backup(local_path, target_name):
    backups = glob.glob(f"{local_path}/{target_name}*.tar.gz")
    if len(backups) == 0:
        return None
    return max(backups, key=os.path.getctime)


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


def untar_volume(target: PrivateerTarget, backup_path):
    volume_mount = docker.types.Mount("/data", target.name)
    backup_mount = docker.types.Mount(f"/backup/{backup_path}", backup_path, type="bind")
    with DockerClient() as cl:
        cl.containers.run(
            "ubuntu",
            remove=True,
            mounts=[volume_mount, backup_mount],
            command=["tar", "xvf", f"/backup/{backup_path}", "-C", "/data", "--strip-components=1"],
        )
    return True
