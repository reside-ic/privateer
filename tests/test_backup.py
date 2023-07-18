import datetime
import os
import tarfile
import tempfile

import docker
import pytest

from src.privateer.backup import backup
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
        res = restore(host, [target])
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
        res = restore(host, [target])
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
