import os
import shutil
import datetime
import time

from src.privateer import cli
from src.privateer.config import PrivateerConfig
from src.privateer.docker_helpers import DockerClient


def test_backup_and_restore():
    cfg = PrivateerConfig("config")
    test = cfg.get_host("test")
    made_dir = False
    if not os.path.exists(test.path):
        os.mkdir(test.path)
        made_dir = True
    try:
        # backup
        res = cli.main(["backup", "config", "--to=test"])
        assert res == "Backed up targets 'orderly_volume', 'another_volume' to host 'test'"
        files = [f for f in os.listdir(test.path) if os.path.isfile(os.path.join(test.path, f))]
        assert len(files) == 2
        # restore
        res = cli.main(["restore", "config", "--from=test"])
        assert res == "Restored targets 'orderly_volume', 'another_volume' from host 'test'"
    finally:
        if made_dir:
            shutil.rmtree(test.path)


def test_restore_no_backups():
    res = cli.main(["restore", "config", "--from=test"])
    assert res == "No valid backups found. Doing nothing."


def test_schedule_and_cancel():
    cfg = PrivateerConfig("config")
    test = cfg.get_host("test")
    made_dir = False
    if not os.path.exists(test.path):
        os.mkdir(test.path)
        made_dir = True
    try:
        # schedule
        res = cli.main(["schedule", "config", "--to=test"])
        assert res == "Scheduling backups of targets 'orderly_volume', 'another_volume' to host 'test'"
        with DockerClient() as cl:
            privateer_containers = [c for c in cl.containers.list() if c.name.startswith("privateer")]
            assert len(privateer_containers) == 1

            # wait 60 seconds for a backup to run
            time.sleep(60)

            # check files backed up
            datetime.datetime.now().strftime("%Y-%m-%dT%H-%M")  # noqa: DTZ005
            files = [f for f in os.listdir(test.path) if os.path.isfile(os.path.join(test.path, f))]
            assert len(files) == 1
            assert files[0].startswith("another_volume-custom")

            # check status
            res = cli.main(["status", "config"])
            assert res == ""

            # stop backups
            res = cli.main(["cancel", "config"])
            assert res == "Canceled all scheduled backups."
            time.sleep(5)
            privateer_containers = [c for c in cl.containers.list() if c.name.startswith("privateer")]
            assert len(privateer_containers) == 0

    finally:
        if made_dir:
            shutil.rmtree(test.path)
