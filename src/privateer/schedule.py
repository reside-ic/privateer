import os
import random
import string
from typing import List

import docker

from privateer.backup import check_host_path
from privateer.config import PrivateerHost, PrivateerTarget
from privateer.docker_helpers import DockerClient

from privateer.docker_helpers import containers_matching


def generate_config(target: PrivateerTarget):
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
    mounts = []
    if host.host_type == "remote":
        env = {"SSH_HOST_NAME": host.hostname, "SSH_REMOTE_PATH": host.path, "SSH_USER": host.user}
        mounts.append(docker.types.Mount("/root/.ssh", os.path.abspath("~/.ssh"), type="bind"))
    else:
        mounts.append(docker.types.Mount("/archive", host.path, type="bind"))
        env = {}
    for t in targets:
        mounts.append(docker.types.Mount(f"/backup/{t.name}", t.name))
        generate_config(t)
    path = os.path.abspath("offen")
    mounts.append(docker.types.Mount("/etc/dockervolumebackup/conf.d", path, type="bind"))
    name = f"privateer_{''.join(random.choices(string.ascii_letters, k=6))}"
    with DockerClient() as cl:
        cl.containers.run("offen/docker-volume-backup:v2",
                          name=name,
                          mounts=mounts,
                          environment=env,
                          detach=True,
                          remove=True)
    return True


def cancel_scheduled_backups():
    running = containers_matching("privateer")
    [r.stop() for r in running]
