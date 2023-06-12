import os
import shutil
import tempfile
from typing import List

import docker
from fabric import Connection
from invoke import UnexpectedExit

from porter.config import PorterHost, PorterTarget
from porter.docker_helpers import DockerClient


def backup(host: PorterHost, targets: List[PorterTarget]):
    if host.host_type == "local":
        if not os.path.exists(host.path):
            msg = f"Host path '{host.path}' does not exist. Either make directory or fix config."
            raise Exception(msg)
        for t in targets:
            path = tar_volume(t)
            res = shutil.copy(path, host.path)
            print(f"Copied {path} to {res}")
    else:
        with Connection(host=host.hostname, user=host.user, port=host.port) as c:
            try:
                c.run(f"test -d {host.path}", in_stream=False)
            except UnexpectedExit:
                msg = f"Host path '{host.path}' does not exist. Either make directory or fix config."
                raise Exception(msg) from None
            for t in targets:
                path = tar_volume(t)
                res = c.put(path, host.path)
                print(f"Uploaded {res.local} to {res.remote}")
    return True


def tar_volume(target: PorterTarget):
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
            command=["tar", "cvf", f"/backup/{target.name}.tar", "-C", "/data", "."],
        )
    return f"{local_backup_path}/{target.name}.tar"


def untar_volume(target: PorterTarget, backup_path):
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
