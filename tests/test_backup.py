import os
import tarfile
import tempfile
from os import listdir

import docker
import pytest

from src.privateer.backup import backup, tar_volume, untar_volume, restore
from src.privateer.config import PrivateerConfig, PrivateerTarget
from src.privateer.docker_helpers import DockerClient


def test_tar_volume():
    test_vol = docker.types.Mount("/data", "privateer_test")
    try:
        with DockerClient() as cl:
            cl.containers.run("ubuntu", mounts=[test_vol], remove=True,
                              command=["touch", "/data/test.txt"])
            target = PrivateerTarget(
                {"name": "privateer_test", "type": "volume"})
            res = tar_volume(target)
            assert res.endswith("privateer_test.tar")
            res = tarfile.open(res)
            tmp = tempfile.mkdtemp()
            res.extractall(tmp)
            files = listdir(tmp)
            assert len(files) == 1
            assert len(files) == 1
            assert files[0] == "test.txt"
    finally:
        v = cl.volumes.get("privateer_test")
        v.remove()


def test_untar_volume():
    test_vol = docker.types.Mount("/data", "privateer_test")
    try:
        with DockerClient() as cl:
            cl.containers.run("ubuntu", mounts=[test_vol], remove=True,
                              command=["touch", "/data/test.txt"])
            target = PrivateerTarget(
                {"name": "privateer_test", "type": "volume"})
            res = tar_volume(target)
            # remove the volume to test restore path
            v = cl.volumes.get("privateer_test")
            v.remove()
            # restore
            res = untar_volume(target, os.path.dirname(res))
            assert res is True
            # check test.txt has been restored to volume
            container = cl.containers.run(
                "ubuntu", mounts=[test_vol], detach=True,
                command=["test", "-f", "/data/test.txt"]
            )
            result = container.wait()
            container.remove()
            assert result["StatusCode"] == 0
    finally:
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
    assert backup(test, cfg.targets)
    assert os.path.isfile(os.path.join(test.path, "orderly_volume.tar"))


def test_restore_local():
    if os.getenv("GITHUB_ACTIONS"):
        pytest.skip("No access to network")
    cfg = PrivateerConfig("config")
    host = cfg.get_host("test")
    host.path = tempfile.mkdtemp()
    test_vol = docker.types.Mount("/data", "privateer_test")
    target = PrivateerTarget({"name": "privateer_test", "type": "volume"})
    with DockerClient() as cl:
        cl.containers.run("ubuntu", mounts=[test_vol], remove=True,
                          command=["touch", "/data/test.txt"])
        backup(host, [target])
        # remove the volume to test restore path
        v = cl.volumes.get("privateer_test")
        v.remove()
        # restore
        res = restore(host, [target])
        assert res is True
        # check test.txt has been restored to volume
        container = cl.containers.run(
            "ubuntu", mounts=[test_vol], detach=True,
            command=["test", "-f", "/data/test.txt"]
        )
        result = container.wait()
        container.remove()
        assert result["StatusCode"] == 0


def test_restore_remote():
    cfg = PrivateerConfig("config")
    host = cfg.get_host("uat")
    test_vol = docker.types.Mount("/data", "privateer_test")
    target = PrivateerTarget({"name": "privateer_test", "type": "volume"})
    with DockerClient() as cl:
        cl.containers.run("ubuntu", mounts=[test_vol], remove=True,
                          command=["touch", "/data/test.txt"])
        backup(host, [target])
        # remove the volume to test restore path
        v = cl.volumes.get("privateer_test")
        v.remove()
        # restore
        res = restore(host, [target])
        assert res is True
        # check test.txt has been restored to volume
        container = cl.containers.run(
            "ubuntu", mounts=[test_vol], detach=True,
            command=["test", "-f", "/data/test.txt"]
        )
        result = container.wait()
        container.remove()
        assert result["StatusCode"] == 0



def test_remote_host_dir_validation():
    if os.getenv("GITHUB_ACTIONS"):
        pytest.skip("No access to network")
    cfg = PrivateerConfig("config")
    uat = cfg.get_host("uat")
    uat.path = "badpath"
    with pytest.raises(Exception) as err:
        backup(uat, cfg.targets)
    assert str(
        err.value) == "Host path 'badpath' does not exist. Either make directory or fix config."


def test_local_host_dir_validation():
    cfg = PrivateerConfig("config")
    test = cfg.get_host("test")
    test.path = "badpath"
    with pytest.raises(Exception) as err:
        backup(test, cfg.targets)
    assert str(
        err.value) == "Host path 'badpath' does not exist. Either make directory or fix config."
