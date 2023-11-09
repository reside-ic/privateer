import docker
from privateer.util import string_from_volume


def check(cfg, name, *, connection=False, quiet=False):
    machine = cfg.machine_config(name)
    vol = machine.key_volume
    try:
        docker.from_env().volumes.get(vol)
    except docker.errors.NotFound:
        msg = f"'{name}' looks unconfigured"
        raise Exception(msg) from None
    found = string_from_volume(vol, "name")
    if found != name:
        msg = f"Configuration is for '{found}', not '{name}'"
        raise Exception(msg)
    if not quiet:
        print(f"Volume '{vol}' looks configured as '{name}'")
    if connection and name in cfg.list_clients():
        _check_connections(cfg, machine)
    return machine


def _check_connections(cfg, machine):
    image = f"mrcide/privateer-client:{cfg.tag}"
    mounts = [
        docker.types.Mount(
            "/privateer/keys", machine.key_volume, type="volume", read_only=True
        )
    ]
    cl = docker.from_env()
    result = {}
    for server in cfg.servers:
        print(
            f"checking connection to '{server.name}' ({server.hostname})...",
            end="",
            flush=True,
        )
        try:
            command = ["ssh", server.name, "cat", "/privateer/keys/name"]
            cl.containers.run(
                image, mounts=mounts, command=command, remove=True
            )
            result[server.name] = True
            print("OK")
        except docker.errors.ContainerError as e:
            result[server.name] = False
            print("ERROR")
            print(e.stderr.decode("utf-8").strip())
    return result
