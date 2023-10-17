"""Usage:
  privateer2 --version
  privateer2 [options] pull
  privateer2 [options] keygen (<name> | --all)
  privateer2 [options] configure <name>
  privateer2 [options] status
  privateer2 [options] check
  privateer2 [options] serve
  privateer2 [options] backup <volume>
  privateer2 [options] restore <volume> [--server=NAME] [--source=NAME]
  privateer2 [options] export <volume> [--to-dir=PATH] [--source=NAME]
  privateer2 [options] import <tarfile> <volume>

Options:
  --path=PATH  The path to the configuration (rather than privateer.json)
  --as=NAME    The machine to run the command as
  --dry-run    Do nothing, but print docker commands

Commentary:
  In all the above '--as' (or <name>) refers to the name of the client
  or server being acted on; the machine we are generating keys for,
  configuring, checking, serving, backing up from or restoring to.

  Note that the 'import' subcommand is quite different and does not
  interact with the configuration; it will reject options '--as' and
  '--path'. If 'volume' exists already, it will fail, so this is
  fairly safe.
"""

import os

import docopt

import docker
import privateer2.__about__ as about
from privateer2.backup import backup
from privateer2.config import read_config
from privateer2.keys import check, configure, keygen, keygen_all
from privateer2.restore import restore
from privateer2.server import serve
from privateer2.tar import export_tar, import_tar


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


def _parse_opts(opts):
    if opts["--version"]:
        return Call(_show_version)

    dry_run = opts["--dry-run"]
    name = opts["--as"]
    if opts["import"]:
        _dont_use("--as", opts, "import")
        _dont_use("--path", opts, "import")
        return Call(
            import_tar,
            volume=opts["<volume>"],
            tarfile=opts["<tarfile>"],
            dry_run=dry_run,
        )

    path_config = opts["--path"] or "privateer.json"
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
            return Call(check, cfg=cfg, name=name)
        elif opts["serve"]:
            return Call(serve, cfg=cfg, name=name, dry_run=dry_run)
        elif opts["backup"]:
            return Call(
                backup,
                cfg=cfg,
                name=name,
                volume=opts["<volume>"],
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
        else:
            msg = "Invalid cli call -- privateer bug"
            raise Exception(msg)


def main(argv=None):
    _parse_argv(argv).run()
