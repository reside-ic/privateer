import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from privateer.vault import hvac, vault_client


class ScheduleJob(BaseModel):
    server: str
    volume: str
    schedule: str


class Schedule(BaseModel):
    port: int | None = None
    container: str = "privateer_scheduler"
    jobs: list[ScheduleJob]


class Server(BaseModel):
    name: str
    hostname: str
    port: int
    key_volume: str
    data_volume: str
    container: str


class Client(BaseModel):
    name: str
    backup: list[str] = []
    key_volume: str = "privateer_keys"
    schedule: Schedule | None = None


class Volume(BaseModel):
    name: str
    local: bool = False


class Vault(BaseModel):
    url: str
    prefix: str
    token: str | None = None

    def client(self) -> hvac.Client:
        return vault_client(self.url, self.token)


class Config(BaseModel):
    servers: list[Server]
    clients: list[Client]
    volumes: list[Volume]
    vault: Vault
    tag: str = "latest"

    def model_post_init(self, __context) -> None:
        _check_config(self)

    def list_servers(self) -> list[str]:
        return [x.name for x in self.servers]

    def list_clients(self) -> list[str]:
        return [x.name for x in self.clients]

    def list_volumes(self) -> list[str]:
        return [x.name for x in self.volumes]

    def machine_config(self, name) -> Server | Client:
        for el in self.servers + self.clients:
            if el.name == name:
                return el
        valid = self.list_servers() + self.list_clients()
        valid_str = ", ".join(f"'{x}'" for x in valid)
        msg = f"Invalid configuration '{name}', must be one of {valid_str}"
        raise Exception(msg)


def read_config(path: str | Path) -> Config:
    """Read configuration from disk.

    Params:

        path: Path to `privateer.json`

    Returns: The privateer configuration.
    """

    with open(path) as f:
        return Config(**json.loads(f.read().strip()))


def _check_config(cfg: Config) -> None:
    servers = cfg.list_servers()
    clients = cfg.list_clients()
    _check_not_duplicated(servers, "servers")
    _check_not_duplicated(clients, "clients")
    err = set(cfg.list_servers()).intersection(set(cfg.list_clients()))
    if err:
        err_str = ", ".join(f"'{nm}'" for nm in err)
        msg = f"Invalid machine listed as both a client and a server: {err_str}"
        raise Exception(msg)
    vols_local = [x.name for x in cfg.volumes if x.local]
    vols_all = [x.name for x in cfg.volumes]
    for cl in cfg.clients:
        for v in cl.backup:
            if v not in vols_all:
                msg = f"Client '{cl.name}' backs up unknown volume '{v}'"
                raise Exception(msg)
            if v in vols_local:
                msg = f"Client '{cl.name}' backs up local volume '{v}'"
                raise Exception(msg)
        if cl.schedule:
            for j in cl.schedule.jobs:
                if j.server not in servers:
                    msg = (
                        f"Client '{cl.name}' scheduling backup to "
                        f"unknown server '{j.server}'"
                    )
                    raise Exception(msg)
                if j.volume not in cl.backup:
                    msg = (
                        f"Client '{cl.name}' scheduling backup of "
                        f"volume '{j.volume}', which it does not back up"
                    )
                    raise Exception(msg)
    if cfg.vault.prefix.startswith("/secret"):
        cfg.vault.prefix = cfg.vault.prefix[7:]


def _check_not_duplicated(els: list[Any], name: str) -> None:
    if len(els) > len(set(els)):
        msg = f"Duplicated elements in {name}"
        raise Exception(msg)
