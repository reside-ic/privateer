import docker
from privateer.check import check
from privateer.config import find_source
from privateer.util import mounts_str, run_container_with_command


def replicate(cfg, name, volume, to, *, source=None, dry_run=False):
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

    # I am a a bit confused about why this is more complex than
    # backup, but it's probable I can simplify once this works.
    image = f"mrcide/privateer-client:{cfg.tag}"
    source = find_source(cfg, volume, source)
    if source:
        mount_data = docker.types.Mount(
            "/privateer/volumes",
            machine.data_volume,
            type="volume",
            read_only=True,
        )
        path_data = f"/privateer/volumes/{source}"
    else:
        mount_data = docker.types.Mount(
            f"/privateer/local/{volume}", volume, type="volume", read_only=True
        )
        path_data = "/privateer/local"
        source = "(local)"
    path_volume = f"{path_data}/{volume}"

    mounts = [
        docker.types.Mount(
            "/privateer/keys", machine.key_volume, type="volume", read_only=True
        ),
        mount_data,
    ]
    command = ["rsync", "-av", "--delete", path_volume, f"{to}:{path_data}"]
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
