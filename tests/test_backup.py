from unittest.mock import MagicMock, call

import vault_dev

import docker
import privateer.server
from privateer.backup import backup
from privateer.config import read_config
from privateer.configure import configure
from privateer.keys import keygen_all


def test_can_print_instructions_to_run_backup(capsys, managed_docker):
    with vault_dev.Server(export_token=True) as server:
        cfg = read_config("example/simple.json")
        cfg.vault.url = server.url()
        vol = managed_docker("volume")
        cfg.clients[0].key_volume = vol
        keygen_all(cfg)
        configure(cfg, "bob")
        capsys.readouterr()  # flush previous output
        backup(cfg, "bob", "data", dry_run=True)
        out = capsys.readouterr()
        lines = out.out.strip().split("\n")
        assert "Command to manually run backup:" in lines
        cmd = (
            "  docker run --rm "
            f"-v {vol}:/privateer/keys:ro -v data:/privateer/volumes/data:ro "
            f"mrcide/privateer-client:{cfg.tag} "
            "rsync -av --delete /privateer/volumes/data "
            "alice:/privateer/volumes/bob"
        )
        assert cmd in lines


def test_can_run_backup(monkeypatch, managed_docker):
    mock_run = MagicMock()
    monkeypatch.setattr(
        privateer.backup, "run_container_with_command", mock_run
    )
    with vault_dev.Server(export_token=True) as server:
        cfg = read_config("example/simple.json")
        cfg.vault.url = server.url()
        vol = managed_docker("volume")
        cfg.clients[0].key_volume = vol
        keygen_all(cfg)
        configure(cfg, "bob")
        backup(cfg, "bob", "data")

        image = f"mrcide/privateer-client:{cfg.tag}"
        command = [
            "rsync",
            "-av",
            "--delete",
            "/privateer/volumes/data",
            "alice:/privateer/volumes/bob",
        ]
        mounts = [
            docker.types.Mount(
                "/privateer/keys", vol, type="volume", read_only=True
            ),
            docker.types.Mount(
                "/privateer/volumes/data", "data", type="volume", read_only=True
            ),
        ]
        assert mock_run.call_count == 1
        assert mock_run.call_args == call(
            "Backup", image, command=command, mounts=mounts
        )
