"""Usage:
  privateer --version
  privateer [options] pull
  privateer [options] keygen (<name> | --all)
  privateer [options] configure <name>
  privateer [options] check [--connection]
  privateer [options] backup <volume> [--server=NAME]
  privateer [options] restore <volume> [--server=NAME] [--source=NAME]
  privateer [options] export <volume> [--to-dir=PATH] [--source=NAME]
  privateer [options] import <tarfile> <volume>
  privateer [options] server (start | stop | status)
  privateer [options] schedule (start | stop | status)

Options:
  --path=PATH  The path to the configuration, or directory with privateer.json
  --as=NAME    The machine to run the command as
  --dry-run    Do nothing, but print docker commands

Commentary:
  In all the above '--as' (or <name>) refers to the name of the client
  or server being acted on; the machine we are generating keys for,
  configuring, checking, serving, backing up from or restoring to.

  Note that the 'import' subcommand is quite different and does not
  interact with the configuration; it will reject options '--as' and
  '--path'. If 'volume' exists already, it will fail, so this is
  fairly safe.  If running export with '--source=local' then the
  configuration is not read - this can be used anywhere to create a
  tar file of a local volume, which is suitable for importing with
  'import'.

  The server and schedule commands start background containers that
  run forever (with the 'start' option). Check in on them with
  'status' or stop them with 'stop'.
"""

import os

import docopt

import docker
import privateer.__about__ as about
from privateer.backup import backup
from privateer.check import check
from privateer.config import read_config
from privateer.configure import configure
from privateer.keys import keygen, keygen_all
from privateer.restore import restore
from privateer.schedule import schedule_start, schedule_status, schedule_stop
from privateer.server import server_start, server_status, server_stop
from privateer.tar import export_tar, export_tar_local, import_tar


def pull(cfg):
    img = [
        f"mrcide/privateer-client:{cfg.tag}",
        f"mrcide/privateer-server:{cfg.tag}",
    ]
    cl = docker.from_env()
    for nm in img:
        print(f"pulling '{nm}'")
        cl.images.pull(nm)


def _dont_use(name, opts, cmd):
    if opts[name]:
        msg = f"Don't use '{name}' with '{cmd}'"
        raise Exception(msg)


def _find_identity(name, root_config):
    if name:
        return name
    path_as = os.path.join(root_config, ".privateer_identity")
    if not os.path.exists(path_as):
        msg = (
            "Can't determine identity; did you forget to configure?"
            "Alternatively, pass '--as=NAME' to this command"
        )
        raise Exception(msg)
    with open(path_as) as f:
        return f.read().strip()


def _do_configure(cfg, name, root):
    configure(cfg, name)
    with open(os.path.join(root, ".privateer_identity"), "w") as f:
        f.write(f"{name}\n")


def _show_version():
    print(f"privateer {about.__version__}")


class Call:
    def __init__(self, target, **kwargs):
        self.target = target
        self.kwargs = kwargs

    def run(self):
        return self.target(**self.kwargs)

    def __eq__(self, other):
        return self.target == other.target and self.kwargs == other.kwargs


def _parse_argv(argv):
    opts = docopt.docopt(__doc__, argv)
    return _parse_opts(opts)


def _path_config(path):
    if not path:
        path = "privateer.json"
    elif os.path.isdir(path):
        path = os.path.join(path, "privateer.json")
    if not os.path.exists(path):
        msg = f"Did not find privateer configuration at '{path}'"
        raise Exception(msg)
    return path


def _parse_opts(opts):
    if opts["--version"]:
        return Call(_show_version)

    dry_run = opts["--dry-run"]
    if opts["import"]:
        _dont_use("--as", opts, "import")
        _dont_use("--path", opts, "import")
        return Call(
            import_tar,
            volume=opts["<volume>"],
            tarfile=opts["<tarfile>"],
            dry_run=dry_run,
        )
    elif opts["export"] and opts["--source"] == "local":
        _dont_use("--as", opts, "export --local")
        _dont_use("--path", opts, "export --local")
        return Call(
            export_tar_local,
            volume=opts["<volume>"],
            to_dir=opts["--to-dir"],
            dry_run=dry_run,
        )

    path_config = _path_config(opts["--path"])
    root_config = os.path.dirname(path_config)
    cfg = read_config(path_config)
    if opts["keygen"]:
        _dont_use("--as", opts, "keygen")
        if opts["--all"]:
            return Call(keygen_all, cfg=cfg)
        else:
            return Call(keygen, cfg=cfg, name=opts["<name>"])
    elif opts["configure"]:
        _dont_use("--as", opts, "configure")
        return Call(
            _do_configure,
            cfg=cfg,
            name=opts["<name>"],
            root=root_config,
        )
    elif opts["pull"]:
        _dont_use("--as", opts, "configure")
        return Call(pull, cfg=cfg)
    else:
        name = _find_identity(opts["--as"], root_config)
        if opts["check"]:
            connection = opts["--connection"]
            return Call(check, cfg=cfg, name=name, connection=connection)
        elif opts["backup"]:
            return Call(
                backup,
                cfg=cfg,
                name=name,
                volume=opts["<volume>"],
                server=opts["--server"],
                dry_run=dry_run,
            )
        elif opts["restore"]:
            return Call(
                restore,
                cfg=cfg,
                name=name,
                volume=opts["<volume>"],
                server=opts["--server"],
                source=opts["--source"],
                dry_run=dry_run,
            )
        elif opts["export"]:
            return Call(
                export_tar,
                cfg=cfg,
                name=name,
                volume=opts["<volume>"],
                to_dir=opts["--to-dir"],
                source=opts["--source"],
                dry_run=dry_run,
            )
        elif opts["server"]:
            if opts["start"]:
                return Call(server_start, cfg=cfg, name=name, dry_run=dry_run)
            elif opts["stop"]:
                return Call(server_stop, cfg=cfg, name=name)
            else:
                return Call(server_status, cfg=cfg, name=name)
        elif opts["schedule"]:
            if opts["start"]:
                return Call(schedule_start, cfg=cfg, name=name, dry_run=dry_run)
            elif opts["stop"]:
                return Call(schedule_stop, cfg=cfg, name=name)
            else:
                return Call(schedule_status, cfg=cfg, name=name)
        else:
            msg = "Invalid cli call -- privateer bug"
            raise Exception(msg)


def main(argv=None):
    _parse_argv(argv).run()
