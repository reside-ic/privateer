import docker

from privateer.config import Client, Config, Server
from privateer.util import string_from_volume


def check(
    cfg: Config, name: str, *, connection: bool = False, quiet: bool = False
) -> Server | Client:
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


def check_client(
    cfg: Config, name: str, *, connection: bool = False, quiet: bool = False
) -> Client:
    machine = check(cfg, name, connection=connection, quiet=quiet)
    if not isinstance(machine, Client):
        msg = f"'{name}' is not a privateer client (it is listed as a server)"
        raise Exception(msg)
    return machine


def check_server(
    cfg: Config, name: str, *, connection: bool = False, quiet: bool = False
) -> Server:
    machine = check(cfg, name, connection=connection, quiet=quiet)
    if not isinstance(machine, Server):
        msg = f"'{name}' is not a privateer server (it is listed as a client)"
        raise Exception(msg)
    return machine


def _check_connections(
    cfg: Config, machine: Server | Client
) -> dict[str, bool]:
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
            e_str = e.stderr.decode("utf-8").strip()  #  type: ignore
            print(e_str)
    return result
