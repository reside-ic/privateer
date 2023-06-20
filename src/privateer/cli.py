"""Usage:
  privateer --version
  privateer backup <path> --to=HOST [--exclude=TARGETS] [--include=TARGETS]
  privateer restore <path> --from=HOST [--exclude=TARGETS] [--include=TARGETS]

Options:
  --exclude=TARGETS  Comma separated string of target names to exclude (default is to include all)
  --include=TARGETS  Comma separated string of target names to include (default is to include all)
"""

import docopt

import privateer.__about__ as about
from privateer.backup import backup, restore
from privateer.config import PrivateerConfig


def main(argv=None):
    opts = docopt.docopt(__doc__, argv)
    if opts["--version"]:
        return about.__version__
    cfg = PrivateerConfig(opts["<path>"])
    targets = get_targets(opts["--include"], opts["--exclude"], cfg.targets)
    if len(targets) == 0:
        return "No targets selected. Doing nothing."
    if opts["backup"]:
        host = cfg.get_host(opts["--to"])
        names = ", ".join([f"'{t.name}'" for t in targets])
        target_str = "targets" if len(targets) > 1 else "target"
        msg = f"Backed up {target_str} {names} to host '{host.name}'"
        backup(host, targets)
        return msg
    elif opts["restore"]:
        host = cfg.get_host(opts["--from"])
        success = restore(host, targets)
        if len(success) > 0:
            names = ", ".join([f"'{s}'" for s in success])
            target_str = "targets" if len(success) > 1 else "target"
            msg = f"Restored {target_str} {names} from host '{host.name}'"
        else:
            msg = "No valid backups found. Doing nothing."
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
