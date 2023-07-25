"""Usage:
  privateer --version
  privateer backup <path> --to=HOST [--exclude=TARGETS] [--include=TARGETS]
  privateer restore <path> --from=HOST [--exclude=TARGETS] [--include=TARGETS] [--y]
  privateer schedule <path> --to=HOST [--exclude=TARGETS] [--include=TARGETS]
  privateer status
  privateer cancel [--host=HOST]

Options:
  --exclude=TARGETS  Comma separated string of target names to exclude (default is to include all)
  --include=TARGETS  Comma separated string of target names to include (default is to include all)
  --host=HOST  Backup host to cancel scheduled backups for (default is to cancel all)
  --y  Restore without further prompting
"""
import json

import docopt

import privateer.__about__ as about
from privateer.backup import backup, cancel_scheduled_backups, list_scheduled_backups, schedule_backups
from privateer.config import PrivateerConfig
from privateer.restore import restore


def main(argv=None):
    opts = docopt.docopt(__doc__, argv)
    if opts["--version"]:
        return about.__version__
    if opts["backup"]:
        return do_backup(opts)
    elif opts["restore"]:
        return do_restore(opts)
    elif opts["schedule"]:
        return schedule(opts)
    elif opts["status"]:
        return get_schedules()
    elif opts["cancel"]:
        return cancel(opts)


def do_backup(opts):
    cfg = PrivateerConfig(opts["<path>"])
    targets = get_targets(opts["--include"], opts["--exclude"], cfg.targets)
    if len(targets) == 0:
        return "No targets selected. Doing nothing."
    host = cfg.get_host(opts["--to"])
    names = ", ".join([f"'{t.name}'" for t in targets])
    target_str = "targets" if len(targets) > 1 else "target"
    msg = f"Backed up {target_str} {names} to host '{host.name}'"
    backup(host, targets)
    return msg


def do_restore(opts):
    cfg = PrivateerConfig(opts["<path>"])
    targets = get_targets(opts["--include"], opts["--exclude"], cfg.targets)
    if len(targets) == 0:
        return "No targets selected. Doing nothing."
    host = cfg.get_host(opts["--from"])
    require_prompt = not opts["--y"]
    success = restore(host, targets, require_prompt)
    if len(success) > 0:
        names = ", ".join([f"'{s}'" for s in success])
        target_str = "targets" if len(success) > 1 else "target"
        msg = f"Restored {target_str} {names} from host '{host.name}'"
    else:
        msg = "No valid backups found. Doing nothing."
    return msg


def schedule(opts):
    cfg = PrivateerConfig(opts["<path>"])
    targets = get_targets(opts["--include"], opts["--exclude"], cfg.targets)
    if len(targets) == 0:
        return "No targets selected. Doing nothing."
    host = cfg.get_host(opts["--to"])
    names = ", ".join([f"'{t.name}'" for t in targets])
    target_str = "targets" if len(targets) > 1 else "target"
    res = schedule_backups(host, targets)
    if res is True:
        return f"Scheduled backups of {target_str} {names} to host '{host.name}'"
    else:
        return f"Scheduling failed. Logs from container:\n {res}"


def get_schedules():
    schedules = list_scheduled_backups()
    num_hosts = len(schedules)
    if num_hosts > 0:
        host_str = "hosts" if num_hosts > 1 else "host"
        msg = f"{num_hosts} {host_str} receiving backups:"
        for s in schedules:
            msg = f"{msg}\n{json.dumps(s, indent=4)}"
        return msg
    else:
        return "No backups scheduled."


def cancel(opts):
    host = opts["--host"]
    cancelled = cancel_scheduled_backups(host)
    num_cancelled = len(cancelled)
    if num_cancelled > 0:
        host_str = "hosts" if len(cancelled) > 1 else "host"
        names = ", ".join([f"'{h}'" for h in cancelled])
        return f"Cancelled all scheduled backups to {host_str} {names}."
    else:
        return "No backups scheduled. Doing nothing."


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
