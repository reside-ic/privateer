"""Usage:
  porter --version
  porter backup <path> --to=HOST [--exclude=TARGETS] [--include=TARGETS]
  porter restore <path> --from=HOST [--exclude=TARGETS] [--include=TARGETS]

Options:
  --exclude=TARGETS  Comma separated string of target names to exclude (default is to include all)
  --include=TARGETS  Comma separated string of target names to include (default is to include all)
"""

import docopt

import porter.__about__ as about
from porter.backup import backup
from porter.config import PorterConfig


def main(argv=None):
    opts = docopt.docopt(__doc__, argv)
    if opts["--version"]:
        return about.__version__
    cfg = PorterConfig(opts["<path>"])
    targets = get_targets(opts["--include"], opts["--exclude"], cfg.targets)
    names = ", ".join([f"'{t.name}'" for t in targets])
    if len(targets) == 0:
        return "No targets selected. Doing nothing."
    if opts["backup"]:
        host = cfg.get_host(opts["--to"])
        msg = f"Backed up targets {names} to host '{host.name}'"
        backup(host, targets)
        return msg
    elif opts["restore"]:
        host = cfg.get_host(opts["--from"])
        msg = f"Restored targets {names} from host '{host.name}'"
        return msg


def get_targets(include, exclude, all_targets):
    if include and exclude:
        msg = "At most one of --include or --exclude should be provided."
        raise Exception(msg)
    if include:
        return [t for t in all_targets if t.name in [i.strip() for i in include.split(",")]]
    elif exclude:
        return [t for t in all_targets if t.name not in [e.strip() for e in exclude.split(",")]]
    else:
        return all_targets
