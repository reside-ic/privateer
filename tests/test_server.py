from unittest.mock import MagicMock, call

import vault_dev

import privateer.server
from privateer.config import read_config
from privateer.configure import configure
from privateer.keys import keygen_all
from privateer.server import server_start, server_status, server_stop


def test_can_print_instructions_to_start_server(capsys, managed_docker):
    with vault_dev.Server(export_token=True) as server:
        cfg = read_config("example/simple.json")
        cfg.vault.url = server.url()
        vol_keys = managed_docker("volume")
        vol_data = managed_docker("volume")
        name = managed_docker("container")
        cfg.servers[0].key_volume = vol_keys
        cfg.servers[0].data_volume = vol_data
        cfg.servers[0].container = name
        keygen_all(cfg)
        configure(cfg, "alice")
        capsys.readouterr()  # flush previous output
        server_start(cfg, "alice", dry_run=True)
        out = capsys.readouterr()
        lines = out.out.strip().split("\n")
        assert "Command to manually launch service container:" in lines
        cmd = (
            f"  docker run --rm -d --name {name} "
            f"-v {vol_keys}:/privateer/keys:ro "
            f"-v {vol_data}:/privateer/volumes "
            f"-p 10022:22 mrcide/privateer-server:{cfg.tag}"
        )
        assert cmd in lines


def test_can_start_server(monkeypatch, managed_docker):
    mock_docker = MagicMock()
    mock_start = MagicMock()
    monkeypatch.setattr(privateer.server, "docker", mock_docker)
    monkeypatch.setattr(privateer.server, "service_start", mock_start)
    with vault_dev.Server(export_token=True) as server:
        cfg = read_config("example/simple.json")
        cfg.vault.url = server.url()
        vol_keys = managed_docker("volume")
        vol_data = managed_docker("volume")
        name = managed_docker("container")
        cfg.servers[0].key_volume = vol_keys
        cfg.servers[0].data_volume = vol_data
        cfg.servers[0].container = name
        keygen_all(cfg)
        configure(cfg, "alice")
        server_start(cfg, "alice")
        mount = mock_docker.types.Mount
        assert mount.call_count == 2
        assert mount.call_args_list[0] == call(
            "/privateer/keys", vol_keys, type="volume", read_only=True
        )
        assert mount.call_args_list[1] == call(
            "/privateer/volumes", vol_data, type="volume"
        )
        assert mock_start.call_count == 1
        image = f"mrcide/privateer-server:{cfg.tag}"
        mounts = [mount.return_value] * 2
        ports = {"22/tcp": 10022}
        assert mock_start.call_args == call(
            "alice",
            name,
            image=image,
            mounts=mounts,
            ports=ports,
            dry_run=False,
        )


def test_can_start_server_with_local_volume(monkeypatch, managed_docker):
    mock_docker = MagicMock()
    mock_start = MagicMock()
    monkeypatch.setattr(privateer.server, "docker", mock_docker)
    monkeypatch.setattr(privateer.server, "service_start", mock_start)
    with vault_dev.Server(export_token=True) as server:
        cfg = read_config("example/local.json")
        cfg.vault.url = server.url()
        vol_keys = managed_docker("volume")
        vol_data = managed_docker("volume")
        vol_other = managed_docker("volume")
        name = managed_docker("container")
        cfg.servers[0].key_volume = vol_keys
        cfg.servers[0].data_volume = vol_data
        cfg.servers[0].container = name
        cfg.volumes[1].name = vol_other
        keygen_all(cfg)
        configure(cfg, "alice")
        server_start(cfg, "alice")
        mount = mock_docker.types.Mount
        assert mount.call_count == 3
        assert mount.call_args_list[0] == call(
            "/privateer/keys", vol_keys, type="volume", read_only=True
        )
        assert mount.call_args_list[1] == call(
            "/privateer/volumes", vol_data, type="volume"
        )
        assert mount.call_args_list[2] == call(
            f"/privateer/local/{vol_other}",
            vol_other,
            type="volume",
            read_only=True,
        )
        assert mock_start.call_count == 1
        image = f"mrcide/privateer-server:{cfg.tag}"
        mounts = [mount.return_value] * 3
        ports = {"22/tcp": 10022}
        assert mock_start.call_args == call(
            "alice",
            name,
            image=image,
            mounts=mounts,
            ports=ports,
            dry_run=False,
        )


def test_can_stop_server(monkeypatch):
    mock_check = MagicMock()
    mock_stop = MagicMock()
    cfg = MagicMock()
    monkeypatch.setattr(privateer.server, "check", mock_check)
    monkeypatch.setattr(privateer.server, "service_stop", mock_stop)
    server_stop(cfg, "alice")
    assert mock_check.call_count == 1
    assert mock_check.call_args == call(cfg, "alice", quiet=True)
    container = mock_check.return_value.container
    assert mock_stop.call_count == 1
    assert mock_stop.call_args == call("alice", container)


def test_can_get_server_status(monkeypatch):
    mock_check = MagicMock()
    mock_status = MagicMock()
    cfg = MagicMock()
    monkeypatch.setattr(privateer.server, "check", mock_check)
    monkeypatch.setattr(privateer.server, "service_status", mock_status)
    server_status(cfg, "alice")
    assert mock_check.call_count == 1
    assert mock_check.call_args == call(cfg, "alice", quiet=False)
    container = mock_check.return_value.container
    assert mock_status.call_count == 1
    assert mock_status.call_args == call(container)
