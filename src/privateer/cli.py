from pathlib import Path

import click

import docker
from privateer.backup import backup
from privateer.check import check
from privateer.config import privateer_root
from privateer.configure import configure, write_identity
from privateer.keys import keygen, keygen_all
from privateer.restore import restore
from privateer.schedule import schedule_start, schedule_status, schedule_stop
from privateer.server import server_start, server_status, server_stop
from privateer.tar import export_tar, export_tar_local, import_tar


class NaturalOrderGroup(click.Group):
    """A click utility to define commands in the order defined.

    See https://github.com/pallets/click/issues/513 for context.
    """

    def list_commands(self, ctx):  # noqa: ARG002
        # This is clearly being used in building the cli, but the
        # coverage checker does not spot that.
        return self.commands.keys()  # no cover


@click.group(cls=NaturalOrderGroup)
@click.version_option()
def cli() -> None:
    """Interact with privateer."""
    pass  # pragma: no cover


help_path = "The path to the configuration, or directory with privateer.json"
help_as = "The machine to run the command as"
help_dry_run = "Do nothing, but print docker commands"
type_path = click.Path(path_type=Path)


@cli.command("pull")
@click.option("--path", type=type_path, help=help_path)
def cli_pull(path: Path | None) -> None:
    """Pull required docker images.

    The tag for images will be pulled from the local configuration
    (privateer.json in the local directory), which falls back on
    `main` if not specified.
    """
    root = privateer_root(path)
    tag = root.config.tag
    img = [
        f"mrcide/privateer-client:{tag}",
        f"mrcide/privateer-server:{tag}",
    ]
    cl = docker.from_env()
    for nm in img:
        print(f"pulling '{nm}'")
        cl.images.pull(nm)


@cli.command("keygen")
@click.argument("name", required=False)
@click.option("--path", type=type_path, help=help_path)
@click.option("--all", is_flag=True, help="Generate all keys")
def cli_keygen(path: Path | None, name: str | None, *, all: bool) -> None:
    """Generate keys for use with privateer.

    Keys will be stored in the vault, on creation, and this will
    overwrite any previously written keys.  You can generate the key
    for a single machine (passing `name=MACHINE`) or all keys at once
    (passing `--all`).

    """
    root = privateer_root(path)
    if all:
        if name is not None:
            msg = "Don't provide 'name' if '--all' is also provided"
            raise RuntimeError(msg)
        keygen_all(root.config)
    else:
        keygen(root.config, name)


@cli.command("configure")
@click.option("--path", type=type_path, help=help_path)
@click.argument("name")
def cli_configure(path: Path | None, name: str) -> None:
    """Configure this machine.

    A machine indicated by the `.privateer_identity` file in the same
    location as `privateer.json`.  This command also updates volumes
    to contain any data required by the role implied by the machine
    name.

    """
    root = privateer_root(path)
    configure(root.config, name)
    write_identity(root.path, name)


@cli.command("check")
@click.option("--path", type=type_path, help=help_path)
@click.option("--as", "name", metavar="NAME", help=help_as)
@click.option("--connection", is_flag=True, help="Check the connection")
def cli_check(path: Path | None, name: str | None, *, connection: bool) -> None:
    """Check privateer configuration and connections.

    This command checks that everything is appropriately configured
    for use as a particular machine.  If `--connection` is passed we
    also check that we can communicate with any servers and can make
    connections with the keys that we hold.

    """
    root = privateer_root(path)
    name = _find_identity(name, root.path)
    check(cfg=root.config, name=name, connection=connection)


@cli.command("backup")
@click.option("--path", type=type_path, help=help_path)
@click.option("--as", "name", metavar="NAME", help=help_as)
@click.option("--dry-run", is_flag=True, help=help_dry_run)
@click.option("--server", metavar="NAME", help="Server to back up to")
@click.argument("volume")
def cli_backup(
    path: Path | None,
    name: str | None,
    volume: str,
    server: str | None,
    *,
    dry_run: bool,
) -> None:
    """Back up a volume to a server.

    Performs a backup of `volume` to `server`.  Uses `rsync` over
    `ssh`; first uses will be slow, but subsequent uses likely much
    faster.

    """
    root = privateer_root(path)
    name = _find_identity(name, root.path)
    backup(
        cfg=root.config,
        name=name,
        volume=volume,
        server=server,
        dry_run=dry_run,
    )


@cli.command("restore")
@click.option("--path", type=type_path, help=help_path)
@click.option("--as", "name", metavar="NAME", help=help_as)
@click.option("--dry-run", is_flag=True, help=help_dry_run)
@click.option("--source", metavar="NAME", help="Source for the data")
@click.option("--server", metavar="NAME", help="Server to pull from")
@click.option(
    "--to-volume", metavar="NAME", help="Alternate volume to restore to"
)
@click.argument("volume")
def cli_restore(
    path: Path | None,
    name: str | None,
    volume: str,
    server: str | None,
    source: str | None,
    to_volume: str | None,
    *,
    dry_run: bool,
) -> None:
    """Restore data to a volume.

    Restores `volume` from `server`.  The `--source` argument controls
    where `server` *originally* received the data from, in the case
    where two different machines are backing up the same volume to a
    server.

    If you provide a volume name with `--to-volume`, you can restore into a
    volume that differs from the upstream name.

    """
    root = privateer_root(path)
    name = _find_identity(name, root.path)
    restore(
        cfg=root.config,
        name=name,
        volume=volume,
        to_volume=to_volume,
        server=server,
        source=source,
        dry_run=dry_run,
    )


@cli.command("export")
@click.option("--path", type=type_path, help=help_path)
@click.option("--as", "name", metavar="NAME", help=help_as)
@click.option("--dry-run", is_flag=True, help=help_dry_run)
@click.option("--to-dir", type=type_path, help="Directory to export to")
@click.option("--source", metavar="NAME", help="Source for the data")
@click.argument("volume")
def cli_export(
    path: Path | None,
    name: str | None,
    volume: str,
    source: str | None,
    to_dir: str | None,
    *,
    dry_run: bool,
) -> None:
    """Export a volume as tar file.

    If using `--source=local` then no configuration is read, this will
    create a tar file of any docker volume.

    """
    if source == "local":
        # Disallow:
        #   --path (no use of root)
        #   --as [name] (requires config)
        export_tar_local(volume=volume, to_dir=to_dir, dry_run=dry_run)
    else:
        root = privateer_root(path)
        export_tar(
            cfg=root.config,
            name=name,
            volume=volume,
            to_dir=to_dir,
            source=source,
            dry_run=dry_run,
        )


@cli.command("import")
@click.option("--dry-run", is_flag=True, help=help_dry_run)
@click.argument("tarfile")
@click.argument("volume")
def cli_import(tarfile: str, volume: str, *, dry_run: bool) -> None:
    """Import a volume from a tarfile.

    Given a tarfile containing the exported contents of a volume,
    import it into a local volume.  This command does not interact
    with any privateer configuration and can be run anywhere.

    If the volume exists already, this command will immediately fail,
    with no data written.

    """
    import_tar(volume=volume, tarfile=tarfile, dry_run=dry_run)


@cli.command("server")
@click.option("--as", "name", metavar="NAME", help=help_as)
@click.option("--path", type=type_path, help=help_path)
@click.option("--dry-run", is_flag=True, help=help_dry_run)
@click.argument("action", type=click.Choice(["start", "stop", "status"]))
def cli_server(
    path: Path | None, name: str, action: str, *, dry_run: bool
) -> None:
    """Interact with the privateer server.

    You can start, stop or get the status of the server.  The server
    is required to receive backups and runs sshd.

    """
    root = privateer_root(path)
    if action == "start":
        server_start(cfg=root.config, name=name, dry_run=dry_run)
    elif action == "stop":
        server_stop(cfg=root.config, name=name)
    else:  # status
        server_status(cfg=root.config, name=name)


@cli.command("schedule")
@click.option("--as", "name", metavar="NAME", help=help_as)
@click.option("--path", type=type_path, help=help_path)
@click.option("--dry-run", is_flag=True, help=help_dry_run)
@click.argument("action", type=click.Choice(["start", "stop", "status"]))
def cli_schedule(
    path: Path | None, name: str, action: str, *, dry_run: bool
) -> None:
    """Interact with the privateer scheduled backups."""
    root = privateer_root(path)
    if action == "start":
        schedule_start(cfg=root.config, name=name, dry_run=dry_run)
    elif action == "stop":
        schedule_stop(cfg=root.config, name=name)
    else:  # status
        schedule_status(cfg=root.config, name=name)


def _find_identity(name: str | None, path: Path) -> str:
    if name:
        return name
    path_as = path / ".privateer_identity"
    if not path_as.exists():
        msg = (
            "Can't determine identity; did you forget to configure?"
            "Alternatively, pass '--as=NAME' to this command"
        )
        raise Exception(msg)
    with path_as.open() as f:
        return f.read().strip()
