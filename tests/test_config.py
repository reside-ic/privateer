import os

import pytest

from src.privateer.config import PrivateerConfig, PrivateerHost, PrivateerTarget


def test_config():
    cfg = PrivateerConfig("config")
    assert len(cfg.targets) == 2
    assert cfg.targets[0].name == "orderly_volume"
    assert len(cfg.hosts) == 4
    assert cfg.hosts[0].name == "production"
    assert cfg.hosts[0].user is None
    assert cfg.hosts[0].port == 10022
    assert cfg.hosts[0].host_type == "remote"
    assert cfg.hosts[0].path == "starport"
    assert cfg.hosts[1].name == "uat"
    assert cfg.hosts[1].hostname == "uat.montagu.dide.ic.ac.uk"
    assert cfg.hosts[1].user == "vagrant"
    assert cfg.hosts[1].port is None
    assert cfg.hosts[1].host_type == "remote"
    assert cfg.hosts[1].path == "starport"
    assert cfg.hosts[2].name == "test"
    assert cfg.hosts[2].path.endswith("starport")
    assert os.path.isabs(cfg.hosts[2].path)
    assert cfg.hosts[2].host_type == "local"


def test_only_volume_targets_allowed():
    with pytest.raises(Exception) as err:
        PrivateerTarget({"name": "test", "type": "directory"})
    assert str(err.value) == "Only 'volume' targets are supported."


def test_valid_host_types():
    with pytest.raises(Exception) as err:
        PrivateerHost({"name": "test", "type": "directory"})
    assert str(err.value) == "Host type must be 'remote' or 'local'."


def test_unique_hosts():
    cfg = PrivateerConfig("config/invalid")
    with pytest.raises(Exception) as err:
        cfg.get_host("annex")
    assert str(err.value) == "Invalid arguments: two hosts with the name 'annex' found."


def test_existent_hosts():
    cfg = PrivateerConfig("config/invalid")
    with pytest.raises(Exception) as err:
        cfg.get_host("badname")
    assert str(err.value) == "Invalid arguments: no host with the name 'badname' found."
