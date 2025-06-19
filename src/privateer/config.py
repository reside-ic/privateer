import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from privateer.vault import hvac, vault_client


class ScheduleJob(BaseModel):
    """Configure a regular backup job.

    Attributes:
        server: The name of the server to back up to.

        volume: The name of the volume to back up.

        schedule: The backup schedule, in "cron" format.  Extension
            formats, such as `@daily` are supported, otherwise use a
            5-element cron specifier.  See <https://crontab.guru/> for
            help generating and interpreting these.

    """

    server: str
    volume: str
    schedule: str


class Schedule(BaseModel):
    """Congfigure schedule for regular backups.

    Attributes:

       jobs: An array of ScheduleJobs, describing a backup task

       port: Optional port, if you want to run the yacron API.  If not
           given, the the API will not be exposed.

       container: Optional name of the container. If not given, we
           default to `privateer_scheduler`

    """

    jobs: list[ScheduleJob]
    port: int | None = None
    container: str = "privateer_scheduler"


class Server(BaseModel):
    """Configuration for a server.

    There are no defaults for any field, so all must be provided.

    Attributes:

        name: A friendly name for the server.  This is the name used
            in all calls to the cli tool, or via the programmatic API.

        hostname: The full hostname for the server

        port: The port to use for ssh.  We do not any ssh server
            already running at the host, but run our own, so if you
            are already running ssh on port 22 you should use a
            different port.

        key_volume: The volume to use to persist keys.  We suggest
            `privateer_<application>_keys,` where `<application>` is
            some short reference to the application being backed up.

        data_volume: The volume to use to persist data.  We suggest
            `privateer_<application>_data`, where `<application>` is
            some short reference to the application being backed up.

        container: The name of the long-running container that will
            run the privateer server.  We suggest
            `privateer_<application>_server`, where `<application>` is
            some short reference to the application being backed up.

    """

    name: str
    hostname: str
    port: int
    key_volume: str
    data_volume: str
    container: str


class Client(BaseModel):
    """Client configuration

    Clients are only ever referred to from the client machine itself
    so we do not need to know their hostname.

    Only the `name` attribute is required.

    Attributes:

        name: A friendly name for the client.  This is the name used
            in all calls to the cli tool, or via the programmatic API.

        backup: An optional array of volumes to back up.  This would
            be empty (or missing, equivalently) on a machine that is
            not the source of truth for any data, such as a staging
            machine.  You can still **restore** from any volume that
            privateer knows about.

        key_volume: The volume to store keys in.  The default is
           `privateer_keys` which may be reasonable but is only what
           you want if the client only acts as a client for a single
           privateer configuration.

        schedule: Optionally a schedule for regular backups
    """

    name: str
    backup: list[str] = []
    key_volume: str = "privateer_keys"
    schedule: Schedule | None = None


class Volume(BaseModel):
    """Describe a volume.

    Attributes:
        name: The name of the volume; this is the same as the name of
            the volume on disk (e.g., listed by `docker volume list`).

        local: An optional boolean indicating if the volume is local
            to the **server**.  This is designed to support a workflow
            where content arrives on the server through some other
            process (in our case it's a barman process that is doing
            continual backup of a Postgres server).
    """

    name: str
    local: bool = False


class Vault(BaseModel):
    """Configure the vault.

    Attributes:
        url: The url of the vault server

        prefix: The path prefix for secrets within a v1 key-value
            store.  This is typically mounted in vault at `/secret/`,
            so something like `/secret/privateer/<application>` is a
            reasonable choice

        token: Optional token (or name of an environment vaiable to
            find this token) to fetch secrets.  If not present and a
            token is required then we look at the environment
            variables `VAULT_TOKEN` and `VAULT_AUTH_GITHUB_TOKEN` (in
            that order) and then prompt interactively for a token.

    """

    url: str
    prefix: str
    token: str | None = None

    def client(self) -> hvac.Client:
        return vault_client(self.url, self.token)


class Config(BaseModel):
    """The privateer configuration.

    Attributes:

        servers: A list of `Server` descriptions.  At least one here
            will be required to do anthing useful.

        clients: A list of `Client` descriptions, including the data
            sources that they will push into the system.  At least one
            here will be required to do anthing useful.

        volumes: A list of `Volume` decriptions.  At least one here
            will be required to do anything useful.

        tag: Optionally, the docker tag to use for `privateer` images.
            The default `latest` will be appropriate unless you are
            testing some new feature.
    """

    servers: list[Server]
    clients: list[Client]
    volumes: list[Volume]
    vault: Vault
    tag: str = "latest"

    def model_post_init(self, __context) -> None:
        _check_config(self)

    def list_servers(self) -> list[str]:
        """List known servers.

        Returns: A list of names of configured servers.
        """
        return [x.name for x in self.servers]

    def list_clients(self) -> list[str]:
        """List known clients.

        Returns: A list of names of configured clients.
        """
        return [x.name for x in self.clients]

    def list_volumes(self) -> list[str]:
        """List known volumes.

        Returns: A list of names of configured volumes.
        """
        return [x.name for x in self.volumes]

    def machine_config(self, name: str) -> Server | Client:
        """Fetch the configuration for a given machine.

        Returns: Configuration for a machine; this has a different
        format for clients and servers, with few overlapping fields.

        """
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
