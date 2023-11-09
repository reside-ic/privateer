from unittest.mock import MagicMock, call

import pytest
import vault_dev

import docker
import privateer.check
from privateer.check import _check_connections, check
from privateer.config import read_config
from privateer.configure import configure
from privateer.keys import keygen_all


def test_can_check_quietly(capsys, managed_docker):
    with vault_dev.Server(export_token=True) as server:
        cfg = read_config("example/simple.json")
        cfg.vault.url = server.url()
        vol = managed_docker("volume")
        cfg.servers[0].key_volume = vol
        keygen_all(cfg)
        configure(cfg, "alice")
        capsys.readouterr()  # flush capture so far
        assert check(cfg, "alice", quiet=True).key_volume == vol
        assert capsys.readouterr().out == ""
        assert check(cfg, "alice", quiet=False).key_volume == vol
        out_loud = capsys.readouterr()
        assert out_loud.out == f"Volume '{vol}' looks configured as 'alice'\n"


def test_error_on_check_if_unconfigured(managed_docker):
    with vault_dev.Server(export_token=True) as server:
        cfg = read_config("example/simple.json")
        cfg.vault.url = server.url()
        vol = managed_docker("volume")
        cfg.servers[0].key_volume = vol
        with pytest.raises(Exception, match="'alice' looks unconfigured"):
            check(cfg, "alice")


def test_error_on_check_if_unknown_machine():
    with vault_dev.Server(export_token=True) as server:
        cfg = read_config("example/simple.json")
        cfg.vault.url = server.url()
        msg = "Invalid configuration 'eve', must be one of 'alice', 'bob'"
        with pytest.raises(Exception, match=msg):
            check(cfg, "eve")


def test_can_check_connections(capsys, monkeypatch, managed_docker):
    mock_docker = MagicMock()
    monkeypatch.setattr(privateer.check, "docker", mock_docker)
    with vault_dev.Server(export_token=True) as server:
        cfg = read_config("example/simple.json")
        cfg.vault.url = server.url()
        vol_keys_bob = managed_docker("volume")
        cfg.servers[0].key_volume = managed_docker("volume")
        cfg.clients[0].key_volume = vol_keys_bob
        keygen_all(cfg)
        configure(cfg, "bob")
        capsys.readouterr()  # flush previous output
        _check_connections(cfg, cfg.clients[0])

        out = capsys.readouterr().out
        assert (
            out == "checking connection to 'alice' (alice.example.com)...OK\n"
        )
        assert mock_docker.from_env.called
        client = mock_docker.from_env.return_value
        mount = mock_docker.types.Mount
        assert mount.call_count == 1
        assert mount.call_args_list[0] == call(
            "/privateer/keys", vol_keys_bob, type="volume", read_only=True
        )
        assert client.containers.run.call_count == 1
        assert client.containers.run.call_args == call(
            f"mrcide/privateer-client:{cfg.tag}",
            mounts=[mount.return_value],
            command=["ssh", "alice", "cat", "/privateer/keys/name"],
            remove=True,
        )


def test_can_report_connection_failure(capsys, monkeypatch, managed_docker):
    mock_docker = MagicMock()
    mock_docker.errors = docker.errors
    err = docker.errors.ContainerError("nm", 1, "ssh", "img", b"the reason")
    monkeypatch.setattr(privateer.check, "docker", mock_docker)
    client = mock_docker.from_env.return_value
    client.containers.run.side_effect = err
    with vault_dev.Server(export_token=True) as server:
        cfg = read_config("example/simple.json")
        cfg.vault.url = server.url()
        vol_keys_bob = managed_docker("volume")
        cfg.servers[0].key_volume = managed_docker("volume")
        cfg.clients[0].key_volume = vol_keys_bob
        keygen_all(cfg)
        configure(cfg, "bob")
        capsys.readouterr()  # flush previous output
        _check_connections(cfg, cfg.clients[0])

        out = capsys.readouterr().out
        assert out == (
            "checking connection to 'alice' (alice.example.com)...ERROR\n"
            "the reason\n"
        )
        assert mock_docker.from_env.called
        client = mock_docker.from_env.return_value
        mount = mock_docker.types.Mount
        assert mount.call_count == 1
        assert mount.call_args_list[0] == call(
            "/privateer/keys", vol_keys_bob, type="volume", read_only=True
        )
        assert client.containers.run.call_count == 1
        assert client.containers.run.call_args == call(
            f"mrcide/privateer-client:{cfg.tag}",
            mounts=[mount.return_value],
            command=["ssh", "alice", "cat", "/privateer/keys/name"],
            remove=True,
        )


def test_only_test_connection_for_clients(monkeypatch, managed_docker):
    mock_check = MagicMock()
    monkeypatch.setattr(privateer.check, "_check_connections", mock_check)
    with vault_dev.Server(export_token=True) as server:
        cfg = read_config("example/simple.json")
        cfg.vault.url = server.url()
        cfg.servers[0].key_volume = managed_docker("volume")
        cfg.servers[0].data_volume = managed_docker("volume")
        cfg.clients[0].key_volume = managed_docker("volume")
        keygen_all(cfg)
        configure(cfg, "alice")
        configure(cfg, "bob")
        check(cfg, "alice")
        assert mock_check.call_count == 0
        check(cfg, "bob")
        assert mock_check.call_count == 0
        check(cfg, "alice", connection=True)
        assert mock_check.call_count == 0
        check(cfg, "bob", connection=True)
        assert mock_check.call_count == 1
        assert mock_check.call_args == call(cfg, cfg.clients[0])
