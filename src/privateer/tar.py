import os

import docker
from privateer.check import check
from privateer.config import find_source
from privateer.util import (
    isotimestamp,
    mounts_str,
    run_container_with_command,
    take_ownership,
    volume_exists,
)


def export_tar(cfg, name, volume, *, to_dir=None, source=None, dry_run=False):
    machine = check(cfg, name, quiet=True)
    source = find_source(cfg, volume, source)
    if not source:
        return export_tar_local(volume, to_dir=to_dir, dry_run=dry_run)

    path = os.path.abspath(to_dir or "")
    mounts = [
        docker.types.Mount("/export", path, type="bind"),
        docker.types.Mount(
            "/privateer", machine.data_volume, type="volume", read_only=True
        ),
    ]
    tarfile = f"{source}-{volume}-{isotimestamp()}.tar"
    src = f"/privateer/{source}/{volume}"
    return _run_tar_create(mounts, src, path, tarfile, dry_run)


def export_tar_local(volume, *, to_dir=None, dry_run=False):
    if not volume_exists(volume):
        msg = f"Volume '{volume}' does not exist"
        raise Exception(msg)

    path = os.path.abspath(to_dir or "")
    mounts = [
        docker.types.Mount("/export", path, type="bind"),
        docker.types.Mount("/privateer", volume, type="volume", read_only=True),
    ]
    tarfile = f"{volume}-{isotimestamp()}.tar"
    src = "/privateer"
    return _run_tar_create(mounts, src, path, tarfile, dry_run)


def import_tar(volume, tarfile, *, dry_run=False):
    if volume_exists(volume):
        msg = f"Volume '{volume}' already exists, please delete first"
        raise Exception(msg)
    if not os.path.exists(tarfile):
        msg = f"Input file '{tarfile}' does not exist"
        raise Exception(msg)

    # Use ubuntu (not alpine) because we will require the -p tag to
    # preserve permissions on tar
    image = "ubuntu"
    tarfile = os.path.abspath(tarfile)
    mounts = [
        docker.types.Mount("/src.tar", tarfile, type="bind", read_only=True),
        docker.types.Mount("/privateer", volume, type="volume"),
    ]
    working_dir = "/privateer"
    command = ["tar", "-xvpf", "/src.tar"]
    if dry_run:
        cmd = [
            "docker",
            "run",
            "--rm",
            *mounts_str(mounts),
            "-w",
            working_dir,
            image,
            *command,
        ]
        print("Command to manually run import:")
        print()
        print(f"  docker volume create {volume}")
        print(f"  {' '.join(cmd)}")
    else:
        docker.from_env().volumes.create(volume)
        run_container_with_command(
            "Import",
            image,
            command=command,
            mounts=mounts,
            working_dir=working_dir,
        )


def _run_tar_create(mounts, src, path, tarfile, dry_run):
    image = "ubuntu"
    command = ["tar", "-cpvf", f"/export/{tarfile}", "."]
    if dry_run:
        cmd = [
            "docker",
            "run",
            "--rm",
            *mounts_str(mounts),
            "-w",
            src,
            image,
            *command,
        ]
        print("Command to manually run export:")
        print()
        print(f"  {' '.join(cmd)}")
        print()
        print("(pay attention to the final '.' in the above command!)")
        print()
        print("Note that this file will have root ownership after creation")
        print(f"You can fix that with 'sudo chown $(whoami) {tarfile}'")
        print("or")
        print()
        cmd_own = take_ownership(tarfile, path, command_only=True)
        print(f"  {' '.join(cmd_own)}")
    else:
        run_container_with_command(
            "Export",
            image,
            command=command,
            mounts=mounts,
            working_dir=src,
        )
        print("Taking ownership of file")
        take_ownership(tarfile, path)
        print(f"Tar file ready at '{path}/{tarfile}'")
    return os.path.join(path, tarfile)
