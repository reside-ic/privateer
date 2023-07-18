import datetime
import os
import shutil
import time
from unittest import mock

from src.privateer import cli
from src.privateer.backup import cancel_scheduled_backups
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
        res = cli.main(["restore", "config", "--from=test", "--y"])
        assert res == "Restored targets 'orderly_volume', 'another_volume' from host 'test'"
    finally:
        if made_dir:
            shutil.rmtree(test.path)


def test_restore_with_prompt():
    cfg = PrivateerConfig("config")
    test = cfg.get_host("test")
    made_dir = False
    if not os.path.exists(test.path):
        os.mkdir(test.path)
        made_dir = True
    try:
        cli.main(["backup", "config", "--to=test"])
        with mock.patch("click.confirm") as prompt:
            prompt.return_value = False
            res = cli.main(["restore", "config", "--from=test"])
            assert res == "No valid backups found. Doing nothing."
        with mock.patch("click.confirm") as prompt:
            prompt.return_value = True
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
        assert res == "Scheduled backups of targets 'orderly_volume', 'another_volume' to host 'test'"
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
            res = cli.main(["status"])
            assert res.startswith("1 host receiving backups:")
            assert '"name": "test"' in res
            assert '"name": "another_volume"' in res

            # stop backups
            res = cli.main(["cancel", "--host=test"])
            assert res == "Cancelled all scheduled backups to host 'test'."
            time.sleep(5)

            privateer_containers = [c for c in cl.containers.list() if c.name.startswith("privateer")]
            assert len(privateer_containers) == 0

            # check status again
            res = cli.main(["status"])
            assert res == "No backups scheduled."
    finally:
        cancel_scheduled_backups(host=None)
        if made_dir:
            shutil.rmtree(test.path)


def test_cancel_no_backups():
    res = cli.main(["cancel"])
    assert res == "No backups scheduled. Doing nothing."


def test_multiple_host_schedules():
    cfg = PrivateerConfig("config")
    test = cfg.get_host("test")
    another = cfg.get_host("another_test")
    if not os.path.exists(another.path):
        os.mkdir(another.path)
    if not os.path.exists(test.path):
        os.mkdir(test.path)
    try:
        # schedule
        res = cli.main(["schedule", "config", "--to=test", "--include=orderly_volume"])
        assert res == "Scheduled backups of target 'orderly_volume' to host 'test'"

        res = cli.main(["schedule", "config", "--to=another_test", "--include=another_volume"])
        assert res == "Scheduled backups of target 'another_volume' to host 'another_test'"

        # check status
        res = cli.main(["status"])
        assert res.startswith("2 hosts receiving backups:")
        assert '"name": "test"' in res
        assert '"name": "orderly_volume"' in res
        assert '"name": "another_test"' in res
        assert '"name": "another_volume"' in res

        # stop backups just for one host
        res = cli.main(["cancel", "--host=test"])
        assert res == "Cancelled all scheduled backups to host 'test'."
        time.sleep(1)

        # check status again
        res = cli.main(["status"])
        assert res.startswith("1 host receiving backups:")
        assert '"name": "another_test"' in res
        assert '"name": "another_volume"' in res
        assert '"name": "test"' not in res
        assert '"name": "orderly_volume"' not in res

        # stop all backups
        res = cli.main(["cancel"])
        assert res == "Cancelled all scheduled backups to host 'another_test'."
        time.sleep(1)

        # check status again
        res = cli.main(["status"])
        assert res == "No backups scheduled."
    finally:
        shutil.rmtree(test.path)
        shutil.rmtree(another.path)
