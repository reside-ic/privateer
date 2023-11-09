import docker
from privateer.check import check
from privateer.config import find_source
from privateer.util import match_value, mounts_str, run_container_with_command


def restore(cfg, name, volume, *, server=None, source=None, dry_run=False):
    machine = check(cfg, name, quiet=True)
    server = match_value(server, cfg.list_servers(), "server")
    volume = match_value(volume, cfg.list_volumes(), "volume")
    source = find_source(cfg, volume, source)
    image = f"mrcide/privateer-client:{cfg.tag}"
    dest_mount = f"/privateer/volumes/{volume}"
    mounts = [
        docker.types.Mount(
            "/privateer/keys", machine.key_volume, type="volume", read_only=True
        ),
        docker.types.Mount(dest_mount, volume, type="volume", read_only=False),
    ]
    if source:
        src = f"{server}:/privateer/volumes/{source}/{volume}/"
    else:
        src = f"{server}:/privateer/local/{volume}/"
        source = "(source)"  # just for printing now
    command = ["rsync", "-av", "--delete", src, f"{dest_mount}/"]
    if dry_run:
        cmd = ["docker", "run", "--rm", *mounts_str(mounts), image, *command]
        print("Command to manually run restore:")
        print()
        print(f"  {' '.join(cmd)}")
        print()
        print(f"This will data from the server '{server}' into into our")
        print(f"local volume '{volume}'; data originally from '{source}'")
        print()
        print("Note that this uses hostname/port information for the server")
        print("contained within (config), along with our identity (id_rsa)")
        print("in the directory /privateer/keys")
    else:
        print(f"Restoring '{volume}' from '{server}'; data originally")
        print(f"from '{source}'")
        run_container_with_command(
            "Restore", image, command=command, mounts=mounts
        )
