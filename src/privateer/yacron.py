import os
import tempfile

import yacron.config

from privateer.backup import backup_command
from privateer.config import Client
from privateer.util import current_timezone_name


def generate_yacron_yaml(cfg, name):
    machine = cfg.machine_config(name)
    if not isinstance(machine, Client) or not machine.schedule:
        return None

    ret = ["defaults:", f'  timezone: "{current_timezone_name()}"']

    if machine.schedule.port:
        ret.append("web:")
        ret.append("  listen:")
        ret.append(f"    - http://0.0.0.0:{machine.schedule.port}")

    ret.append("jobs:")
    for i, job in enumerate(machine.schedule.jobs):
        job_name = f"job-{i + 1}"
        cmd = " ".join(backup_command(name, job.volume, job.server))
        ret.append(f'  - name: "{job_name}"')
        ret.append(f'    command: "{cmd}"')
        ret.append(f'    schedule: "{job.schedule}"')

    _validate_yacron_yaml(ret)
    return ret


def _validate_yacron_yaml(text):
    text = "".join(f"{x}\n" for x in text)
    try:
        fd, tmp = tempfile.mkstemp(text=True)
        with os.fdopen(fd, "w") as f:
            f.write(text)
        yacron.config.parse_config(tmp)
        return True
    finally:
        os.remove(tmp)
