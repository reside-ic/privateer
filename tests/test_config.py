import pytest

from src.porter.config import PorterConfig, PorterTarget


def test_config():
    cfg = PorterConfig("config")
    assert len(cfg.targets) == 1
    assert cfg.targets[0].name == "orderly_volume"
    assert len(cfg.hosts) == 2
    assert cfg.hosts[0].name == "annex"
    assert cfg.hosts[0].hostname == "annex.montagu.dide.ic.ac.uk"
    assert cfg.hosts[0].user == "montagu"
    assert cfg.hosts[0].port is None
    assert cfg.hosts[1].name == "production"
    assert cfg.hosts[1].user is None
    assert cfg.hosts[1].port == 10022


def test_only_volume_targets_allowed():
    with pytest.raises(Exception) as err:
        PorterTarget({"name": "test", "type": "directory"})
    assert str(err.value) == "Only 'volume' targets are supported."


def test_unique_hosts():
    cfg = PorterConfig("config/invalid")
    with pytest.raises(Exception) as err:
        cfg.get_host("annex")
    assert str(err.value) == "Invalid arguments: two hosts with the name 'annex' found."
