import docker
from privateer.check import check
from privateer.config import find_source
from privateer.util import mounts_str, run_container_with_command


def replicate(cfg, name, volume, to, *, source=None, dry_run=True):
    machine = check(cfg, name, quiet=True)
    if name not in cfg.list_servers():
        msg = f"Can only replicate from servers, but '{name}' is a client"
        raise Exception(msg)
    if to not in cfg.list_servers():
        msg = f"Can only replicate to servers, but '{to}' is a client"
        raise Exception(msg)
    if to == name:
        msg = f"Can't replicate to ourselves ('{to}')"
        raise Exception(msg)

    image = f"mrcide/privateer-client:{cfg.tag}"
    source = find_source(cfg, volume, source)
    if source:
        mount_data = docker.types.Mount(
            "/privateer/volumes",
            machine.data_volume,
            type="volume",
            read_only=True,
        )
        path_data = f"/privateer/volumes/{source}/{volume}"
    else:
        mount_data = docker.types.Mount(
            f"/privateer/local/{volume}", volume, type="volume", read_only=True
        )
        path_data = f"/privateer/local/{volume}"
        source = "(local)"

    mounts = [
        mount_data,
        docker.types.Mount(
            "/privateer/keys", machine.key_volume, type="volume", read_only=True
        ),
    ]
    command = ["rsync", "-av", "--delete", path_data, f"{to}:{path_data}"]
    if dry_run:
        cmd = ["docker", "run", "--rm", *mounts_str(mounts), image, *command]
        print("Command to manually run replication:")
        print()
        print(f"  {' '.join(cmd)}")
    else:
        print(f"Replicating '{volume}' from '{name}' to '{to}'")
        run_container_with_command(
            "Replication", image, command=command, mounts=mounts
        )
