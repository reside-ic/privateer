import json
from pathlib import Path

from pydantic import BaseModel

from privateer.util import match_value
from privateer.vault import vault_client


def read_config(path):
    with open(path) as f:
        return Config(**json.loads(f.read().strip()))


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

    def client(self):
        return vault_client(self.url, self.token)


class Config(BaseModel):
    servers: list[Server]
    clients: list[Client]
    volumes: list[Volume]
    vault: Vault
    tag: str = "latest"

    def model_post_init(self, __context):
        _check_config(self)

    def list_servers(self):
        return [x.name for x in self.servers]

    def list_clients(self):
        return [x.name for x in self.clients]

    def list_volumes(self):
        return [x.name for x in self.volumes]

    def machine_config(self, name):
        for el in self.servers + self.clients:
            if el.name == name:
                return el
        valid = self.list_servers() + self.list_clients()
        valid_str = ", ".join(f"'{x}'" for x in valid)
        msg = f"Invalid configuration '{name}', must be one of {valid_str}"
        raise Exception(msg)


class Root(BaseModel):
    config: Config
    path: Path


def privateer_root(path: Path | None) -> Root:
    if path is None:
        path = Path("privateer.json")
    elif path.is_dir():
        path = path / "privateer.json"
    if not path.exists():
        msg = f"Did not find privateer configuration at '{path}'"
        raise Exception(msg)
    return Root(config=read_config(path), path=path.parent)


# this could be put elsewhere; we find the plausible sources (original
# clients) that backed up a source to any server.
def find_source(cfg, volume, source):
    if volume not in cfg.list_volumes():
        msg = f"Unknown volume '{volume}'"
        raise Exception(msg)
    for v in cfg.volumes:
        if v.name == volume and v.local:
            if source is not None:
                msg = f"'{volume}' is a local source, so 'source' must be empty"
                raise Exception(msg)
            return None
    pos = [cl.name for cl in cfg.clients if volume in cl.backup]
    return match_value(source, pos, "source")


def _check_config(cfg):
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


def _check_not_duplicated(els, name):
    if len(els) > len(set(els)):
        msg = f"Duplicated elements in {name}"
        raise Exception(msg)
