import glob
import os
import tempfile
from typing import List

import click
import docker
from fabric import Connection

from privateer.config import PrivateerHost, PrivateerTarget
from privateer.docker_helpers import DockerClient


def restore_local_backup(host: PrivateerHost, target: PrivateerTarget, require_prompt):
    path = get_most_recent_backup(host.path, target.name)
    if path is None:
        msg = f"No backups found. Not restoring {target.name}"
        print(msg)
        return False
    else:
        if not require_prompt or click.confirm(f"About to restore file {path}. Continue?", default=True):
            untar_volume(target, path)
            print(f"Restored {path} to {target.name}")
            return True
        return False


def restore_remote_backup(
    host: PrivateerHost, target: PrivateerTarget, c: Connection, local_backup_path, require_prompt
):
    res = c.run(f"ls -t {host.path}/{target.name}-*.tar.gz | head -1", in_stream=False, pty=True)
    if res.ok:
        file = res.stdout.strip()
        if not require_prompt or click.confirm(f"About to restore file {file}. Continue?", default=True):
            c.get(file, f"{local_backup_path}/")
            untar_volume(target, f"{local_backup_path}/{os.path.basename(file)}")
            print(f"Restored {file} to {target.name}")
            return True
        else:
            return False
    else:
        msg = f"No backups found. Not restoring {target.name}"
        print(msg)
        return False


def restore(host: PrivateerHost, targets: List[PrivateerTarget], require_prompt):
    success = []
    if host.host_type == "local":
        for t in targets:
            if restore_local_backup(host, t, require_prompt):
                success.append(t.name)
    else:
        with Connection(host=host.hostname, user=host.user, port=host.port) as c:
            with tempfile.TemporaryDirectory() as local_backup_path:
                for t in targets:
                    if restore_remote_backup(host, t, c, local_backup_path, require_prompt):
                        success.append(t.name)
    return success


def get_most_recent_backup(local_path, target_name):
    backups = glob.glob(f"{local_path}/{target_name}*.tar.gz")
    if len(backups) == 0:
        return None
    return max(backups, key=os.path.getctime)


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
