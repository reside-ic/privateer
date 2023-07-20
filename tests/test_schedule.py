import datetime
import os
import tempfile
import time

from src.privateer.backup import cancel_scheduled_backups, schedule_backups
from src.privateer.config import PrivateerConfig
from src.privateer.docker_helpers import DockerClient


def test_schedules():
    cfg = PrivateerConfig("config")
    host = cfg.get_host("test")
    host.path = tempfile.mkdtemp()
    assert schedule_backups(host, cfg.targets)
    with DockerClient() as cl:
        privateer_containers = [c for c in cl.containers.list() if c.name.startswith("privateer")]
        assert len(privateer_containers) == 1

        # wait 60 seconds for a backup to run
        time.sleep(60)

        # check files backed up
        datetime.datetime.now().strftime("%Y-%m-%dT%H-%M")  # noqa: DTZ005
        files = [f for f in os.listdir(host.path) if os.path.isfile(os.path.join(host.path, f))]
        assert len(files) == 1
        assert files[0].startswith("another_volume-custom")

        # stop backups
        cancel_scheduled_backups(host=None)
        time.sleep(5)
        privateer_containers = [c for c in cl.containers.list() if c.name.startswith("privateer")]
        assert len(privateer_containers) == 0
