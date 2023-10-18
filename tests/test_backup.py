from unittest.mock import MagicMock, call

import vault_dev

import docker
import privateer2.server
from privateer2.backup import backup
from privateer2.config import read_config
from privateer2.keys import configure, keygen_all


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
            f"-v {vol}:/privateer/keys:ro -v data:/privateer/data:ro "
            "mrcide/privateer-client:docker "
            "rsync -av --delete /privateer/data alice:/privateer/volumes/bob"
        )
        assert cmd in lines


def test_can_run_backup(monkeypatch, managed_docker):
    mock_run = MagicMock()
    monkeypatch.setattr(privateer2.backup, "run_docker_command", mock_run)
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
            "/privateer/data",
            "alice:/privateer/volumes/bob",
        ]
        mounts = [
            docker.types.Mount(
                "/privateer/keys", vol, type="volume", read_only=True
            ),
            docker.types.Mount(
                "/privateer/data", "data", type="volume", read_only=True
            ),
        ]
        assert mock_run.call_count == 1
        assert mock_run.call_args == call(
            "Backup", image, command=command, mounts=mounts
        )
