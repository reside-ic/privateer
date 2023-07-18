import datetime
import os
import tarfile
import tempfile
from unittest import mock

import docker
import pytest

from src.privateer.backup import backup, generate_backup_config
from src.privateer.config import PrivateerConfig, PrivateerTarget
from src.privateer.docker_helpers import DockerClient
from src.privateer.restore import get_most_recent_backup, restore, untar_volume


def test_tar_volume():
    test_vol = docker.types.Mount("/data", "privateer_test")
    with DockerClient() as cl:
        cl.containers.run("ubuntu", mounts=[test_vol], remove=True, command=["touch", "/data/test.txt"])
        target = PrivateerTarget({"name": "privateer_test", "type": "volume"})
        res = tar_volume(target)
        assert res.endswith("privateer_test.tar")
        res = tarfile.open(res)
        tmp = tempfile.mkdtemp()
        res.extractall(tmp)
        files = os.listdir(tmp)
        assert len(files) == 1
        assert len(files) == 1
        assert files[0] == "test.txt"
        v = cl.volumes.get("privateer_test")
        v.remove()


def test_untar_volume():
    test_vol = docker.types.Mount("/data", "privateer_test")
    with DockerClient() as cl:
        cl.containers.run("ubuntu", mounts=[test_vol], remove=True, command=["touch", "/data/test.txt"])
        target = PrivateerTarget({"name": "privateer_test", "type": "volume"})
        res = tar_volume(target)
        # remove the volume to test restore path
        v = cl.volumes.get("privateer_test")
        v.remove()
        # restore
        res = untar_volume(target, res)
        assert res is True
        # check test.txt has been restored to volume
        container = cl.containers.run(
            "ubuntu", mounts=[test_vol], detach=True, command=["test", "-f", "/data/test.txt"]
        )
        result = container.wait()
        container.remove()
        assert result["StatusCode"] == 0
        v = cl.volumes.get("privateer_test")
        v.remove()


def test_backup_remote():
    if os.getenv("GITHUB_ACTIONS"):
        pytest.skip("No access to network")
    cfg = PrivateerConfig("config")
    assert backup(cfg.get_host("uat"), cfg.targets)


def test_backup_local():
    cfg = PrivateerConfig("config")
    test = cfg.get_host("test")
    test.path = tempfile.mkdtemp()
    now = datetime.datetime.now().strftime("%Y-%m-%dT%H")  # noqa: DTZ005
    assert backup(test, cfg.targets)
    files = [f for f in os.listdir(test.path) if os.path.isfile(os.path.join(test.path, f))]
    assert len(files) == 2
    assert os.path.basename(get_most_recent_backup(test.path, "orderly_volume")) in files
    assert os.path.basename(get_most_recent_backup(test.path, "another_volume")) in files
    assert now in files[0]
    assert now in files[1]


def test_restore_local():
    cfg = PrivateerConfig("config")
    host = cfg.get_host("test")
    host.path = tempfile.mkdtemp()
    test_vol = docker.types.Mount("/data", "privateer_test")
    target = PrivateerTarget({"name": "privateer_test", "type": "volume"})
    with DockerClient() as cl:
        cl.containers.run("ubuntu", mounts=[test_vol], remove=True, command=["touch", "/data/test.txt"])
        backup(host, [target])
        # remove the volume to test restore path
        v = cl.volumes.get("privateer_test")
        v.remove()
        # restore
        with mock.patch("click.confirm") as prompt:
            prompt.return_value = True
            res = restore(host, [target], prompt=False)
            assert res == ["privateer_test"]
        # check test.txt has been restored to volume
        container = cl.containers.run(
            "ubuntu", mounts=[test_vol], detach=True, command=["test", "-f", "/data/test.txt"]
        )
        result = container.wait()
        container.remove()
        assert result["StatusCode"] == 0
        v = cl.volumes.get("privateer_test")
        v.remove()


def test_local_restore_prompt():
    cfg = PrivateerConfig("config")
    host = cfg.get_host("test")
    host.path = tempfile.mkdtemp()
    target = PrivateerTarget({"name": "privateer_test", "type": "volume"})
    backup(host, [target])
    with mock.patch("click.confirm") as prompt:
        prompt.return_value = False
        res = restore(host, [target], prompt=True)
        # when prompt is answered in the negative, nothing gets restored
        assert len(res) == 0
    with mock.patch("click.confirm") as prompt:
        prompt.return_value = True
        res = restore(host, [target], prompt=True)
        # when prompt is answered in the affirmative, restore happens
        assert len(res) == 1
    with DockerClient() as cl:
        v = cl.volumes.get("privateer_test")
        v.remove()


def test_restore_remote():
    if os.getenv("GITHUB_ACTIONS"):
        pytest.skip("No access to network")
    cfg = PrivateerConfig("config")
    host = cfg.get_host("uat")
    test_vol = docker.types.Mount("/data", "privateer_test")
    target = PrivateerTarget({"name": "privateer_test", "type": "volume"})
    with DockerClient() as cl:
        cl.containers.run("ubuntu", mounts=[test_vol], remove=True, command=["touch", "/data/test.txt"])
        backup(host, [target])
        # remove the volume to test restore path
        v = cl.volumes.get("privateer_test")
        v.remove()
        # restore
        res = restore(host, [target], prompt=False)
        assert res == ["privateer_test"]

        # check test.txt has been restored to volume
        container = cl.containers.run(
            "ubuntu", mounts=[test_vol], detach=True, command=["test", "-f", "/data/test.txt"]
        )
        result = container.wait()
        container.remove()
        assert result["StatusCode"] == 0
        v = cl.volumes.get("privateer_test")
        v.remove()


def test_remote_restore_prompt():
    if os.getenv("GITHUB_ACTIONS"):
        pytest.skip("No access to network")
    cfg = PrivateerConfig("config")
    host = cfg.get_host("uat")
    target = PrivateerTarget({"name": "privateer_test", "type": "volume"})
    backup(host, [target])
    with mock.patch("click.confirm") as prompt:
        prompt.return_value = False
        res = restore(host, [target], prompt=True)
        # when prompt is answered in the negative, nothing gets restored
        assert len(res) == 0
    with mock.patch("click.confirm") as prompt:
        prompt.return_value = True
        res = restore(host, [target], prompt=True)
        # when prompt is answered in the affirmative, restore happens
        assert len(res) == 1
    with DockerClient() as cl:
        v = cl.volumes.get("privateer_test")
        v.remove()


def test_remote_host_dir_validation():
    if os.getenv("GITHUB_ACTIONS"):
        pytest.skip("No access to network")
    cfg = PrivateerConfig("config")
    uat = cfg.get_host("uat")
    uat.path = "badpath"
    with pytest.raises(Exception) as err:
        backup(uat, cfg.targets)
    assert str(err.value) == "Host path 'badpath' does not exist. Either make directory or fix config."


def test_local_host_dir_validation():
    cfg = PrivateerConfig("config")
    test = cfg.get_host("test")
    test.path = "badpath"
    with pytest.raises(Exception) as err:
        backup(test, cfg.targets)
    assert str(err.value) == "Host path 'badpath' does not exist. Either make directory or fix config."


def test_backup_config():
    cfg = PrivateerConfig("config")
    target = cfg.targets[0]
    tmp = tempfile.gettempdir()
    path = os.path.join(tmp, "test_offen_config")
    if not os.path.exists(path):
        os.mkdir(path)
    generate_backup_config(target, path)
    files = [f for f in os.listdir(path) if os.path.isfile(os.path.join(path, f))]
    assert len(files) == 3

    machine = os.uname().nodename

    daily = [f for f in files if "daily" in f][0]
    lines = open(os.path.join(path, daily)).read().split("\n")
    assert lines[0] == 'BACKUP_SOURCES="/backup/orderly_volume"'
    assert lines[1] == f'BACKUP_FILENAME="orderly_volume-daily-{machine}-%Y-%m-%dT%H-%M-%S.tar.gz"'
    assert lines[2] == f'BACKUP_PRUNING_PREFIX="orderly_volume-daily-{machine}-"'
    assert lines[3] == 'BACKUP_CRON_EXPRESSION="0 2 * * *"'
    assert lines[4] == 'BACKUP_RETENTION_DAYS="7"'

    monthly = [f for f in files if "monthly" in f][0]
    lines = open(os.path.join(path, monthly)).read().split("\n")
    lines = [line for line in lines if line]
    assert lines[0] == 'BACKUP_SOURCES="/backup/orderly_volume"'
    assert lines[1] == f'BACKUP_FILENAME="orderly_volume-monthly-{machine}-%Y-%m-%dT%H-%M-%S.tar.gz"'
    assert lines[2] == f'BACKUP_PRUNING_PREFIX="orderly_volume-monthly-{machine}-"'
    assert lines[3] == 'BACKUP_CRON_EXPRESSION="0 4 1 * *"'
    assert len(lines) == 4


def tar_volume(target: PrivateerTarget):
    tmp = tempfile.gettempdir()
    local_backup_path = os.path.join(tmp, "backup")
    if not os.path.exists(local_backup_path):
        os.mkdir(local_backup_path)
    volume_mount = docker.types.Mount("/data", target.name)
    backup_mount = docker.types.Mount("/backup", local_backup_path, type="bind")
    with DockerClient() as cl:
        cl.containers.run(
            "ubuntu",
            remove=True,
            mounts=[volume_mount, backup_mount],
            command=["tar", "cvf", f"/backup/{target.name}.tar", "-C", "/data", "."],
        )
    return f"{local_backup_path}/{target.name}.tar"
