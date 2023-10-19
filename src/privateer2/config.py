import json
from typing import List

from pydantic import BaseModel

from privateer2.util import match_value
from privateer2.vault import vault_client


def read_config(path):
    with open(path) as f:
        return Config(**json.loads(f.read().strip()))


class Server(BaseModel):
    name: str
    hostname: str
    port: int
    key_volume: str = "privateer_keys"
    data_volume: str = "privateer_data"
    container: str = "privateer_server"


class Client(BaseModel):
    name: str
    backup: List[str] = []
    restore: List[str] = []
    key_volume: str = "privateer_keys"


class Volume(BaseModel):
    name: str
    local: bool = False


class Vault(BaseModel):
    url: str
    prefix: str

    def client(self):
        return vault_client(self.url)


class Config(BaseModel):
    servers: List[Server]
    clients: List[Client]
    volumes: List[Volume]
    vault: Vault
    tag: str = "prototype"

    def model_post_init(self, __context):
        _check_config(self)

    def list_servers(self):
        return [x.name for x in self.servers]

    def list_clients(self):
        return [x.name for x in self.clients]

    def machine_config(self, name):
        for el in self.servers + self.clients:
            if el.name == name:
                return el
        valid = self.list_servers() + self.list_clients()
        valid_str = ", ".join(f"'{x}'" for x in valid)
        msg = f"Invalid configuration '{name}', must be one of {valid_str}"
        raise Exception(msg)


# this could be put elsewhere; we find the plausible sources (original
# clients) that backed up a source to any server.
def find_source(cfg, volume, source):
    for v in cfg.volumes:
        if v.name == volume and v.local:
            if source is not None:
                msg = f"'{volume}' is a local source, so 'source' must be empty"
                raise Exception(msg)
            return "local"
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
        for v in cl.restore:
            if v not in vols_all:
                msg = f"Client '{cl.name}' restores from unknown volume '{v}'"
                raise Exception(msg)
        for v in cl.backup:
            if v not in vols_all:
                msg = f"Client '{cl.name}' backs up unknown volume '{v}'"
                raise Exception(msg)
            if v in vols_local:
                msg = f"Client '{cl.name}' backs up local volume '{v}'"
                raise Exception(msg)
    if cfg.vault.prefix.startswith("/secret"):
        cfg.vault.prefix = cfg.vault.prefix[7:]


def _check_not_duplicated(els, name):
    if len(els) > len(set(els)):
        msg = f"Duplicated elements in {name}"
        raise Exception(msg)
