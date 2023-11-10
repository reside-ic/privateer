from unittest.mock import MagicMock, call

import pytest
import vault_dev

import privateer.schedule
from privateer.config import read_config
from privateer.configure import configure
from privateer.keys import keygen_all
from privateer.schedule import schedule_start, schedule_status, schedule_stop


def test_can_print_instructions_to_start_schedule(capsys, managed_docker):
    with vault_dev.Server(export_token=True) as schedule:
        cfg = read_config("example/schedule.json")
        cfg.vault.url = schedule.url()
        vol_keys = managed_docker("volume")
        vol_data1 = managed_docker("volume")
        vol_data2 = managed_docker("volume")
        name = managed_docker("container")
        cfg.clients[0].key_volume = vol_keys
        cfg.clients[0].backup = [vol_data1, vol_data2]
        cfg.clients[0].backup = [vol_data1, vol_data2]
        cfg.clients[0].schedule.container = name
        cfg.clients[0].schedule.jobs[0].volume = vol_data1
        cfg.clients[0].schedule.jobs[1].volume = vol_data2
        keygen_all(cfg)
        configure(cfg, "bob")
        capsys.readouterr()  # flush previous output
        schedule_start(cfg, "bob", dry_run=True)
        out = capsys.readouterr()
        lines = out.out.strip().split("\n")
        assert "Command to manually launch service container:" in lines
        cmd = (
            f"  docker run --rm -d --name {name} "
            f"-v {vol_keys}:/privateer/keys:ro "
            f"-v {vol_data1}:/privateer/volumes/{vol_data1}:ro "
            f"-v {vol_data2}:/privateer/volumes/{vol_data2}:ro "
            f"-p 8080:8080 mrcide/privateer-client:{cfg.tag} "
            "yacron -c /privateer/keys/yacron.yml"
        )
        assert cmd in lines


def test_can_start_schedule(monkeypatch, managed_docker):
    mock_docker = MagicMock()
    mock_start = MagicMock()
    monkeypatch.setattr(privateer.schedule, "docker", mock_docker)
    monkeypatch.setattr(privateer.schedule, "service_start", mock_start)
    with vault_dev.Server(export_token=True) as schedule:
        cfg = read_config("example/schedule.json")
        cfg.vault.url = schedule.url()
        vol_keys = managed_docker("volume")
        vol_data1 = managed_docker("volume")
        vol_data2 = managed_docker("volume")
        name = managed_docker("container")
        cfg.clients[0].key_volume = vol_keys
        cfg.clients[0].backup = [vol_data1, vol_data2]
        cfg.clients[0].backup = [vol_data1, vol_data2]
        cfg.clients[0].schedule.container = name
        cfg.clients[0].schedule.jobs[0].volume = vol_data1
        cfg.clients[0].schedule.jobs[1].volume = vol_data2
        keygen_all(cfg)
        configure(cfg, "bob")
        schedule_start(cfg, "bob")
        mount = mock_docker.types.Mount
        assert mount.call_count == 3
        assert mount.call_args_list[0] == call(
            "/privateer/keys", vol_keys, type="volume", read_only=True
        )
        assert mount.call_args_list[1] == call(
            f"/privateer/volumes/{vol_data1}",
            vol_data1,
            type="volume",
            read_only=True,
        )
        assert mount.call_args_list[2] == call(
            f"/privateer/volumes/{vol_data2}",
            vol_data2,
            type="volume",
            read_only=True,
        )
        assert mock_start.call_count == 1
        assert mock_start.call_args == call(
            "bob",
            name,
            image=f"mrcide/privateer-client:{cfg.tag}",
            mounts=[mount.return_value] * 3,
            ports={"8080/tcp": 8080},
            command=["yacron", "-c", "/privateer/keys/yacron.yml"],
            dry_run=False,
        )


def test_cant_schedule_clients_with_no_schedule(managed_docker):
    with vault_dev.Server(export_token=True) as server:
        cfg = read_config("example/simple.json")
        cfg.vault.url = server.url()
        vol = managed_docker("volume")
        cfg.clients[0].key_volume = vol
        keygen_all(cfg)
        configure(cfg, "bob")
        msg = "A schedule is not defined in the configuration for 'bob'"
        with pytest.raises(Exception, match=msg):
            schedule_start(cfg, "bob", dry_run=True)


def test_can_stop_schedule(monkeypatch):
    mock_check = MagicMock()
    mock_stop = MagicMock()
    cfg = MagicMock()
    monkeypatch.setattr(privateer.schedule, "check", mock_check)
    monkeypatch.setattr(privateer.schedule, "service_stop", mock_stop)
    schedule_stop(cfg, "bob")
    assert mock_check.call_count == 1
    assert mock_check.call_args == call(cfg, "bob", quiet=True)
    container = mock_check.return_value.schedule.container
    assert mock_stop.call_count == 1
    assert mock_stop.call_args == call("bob", container)


def test_can_get_schedule_status(monkeypatch):
    mock_check = MagicMock()
    mock_status = MagicMock()
    cfg = MagicMock()
    monkeypatch.setattr(privateer.schedule, "check", mock_check)
    monkeypatch.setattr(privateer.schedule, "service_status", mock_status)
    schedule_status(cfg, "bob")
    assert mock_check.call_count == 1
    assert mock_check.call_args == call(cfg, "bob", quiet=False)
    container = mock_check.return_value.schedule.container
    assert mock_status.call_count == 1
    assert mock_status.call_args == call(container)
