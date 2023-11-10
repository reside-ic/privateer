from unittest.mock import MagicMock, call

import vault_dev

import docker
import privateer.config
import privateer.restore
from privateer.config import read_config
from privateer.configure import configure
from privateer.keys import keygen_all
from privateer.restore import restore


def test_can_print_instructions_to_run_restore(capsys, managed_docker):
    with vault_dev.Server(export_token=True) as server:
        cfg = read_config("example/simple.json")
        cfg.vault.url = server.url()
        vol = managed_docker("volume")
        cfg.clients[0].key_volume = vol
        keygen_all(cfg)
        configure(cfg, "bob")
        capsys.readouterr()  # flush previous output
        restore(cfg, "bob", "data", dry_run=True)
        out = capsys.readouterr()
        lines = out.out.strip().split("\n")
        assert "Command to manually run restore:" in lines
        cmd = (
            "  docker run --rm "
            f"-v {vol}:/privateer/keys:ro -v data:/privateer/volumes/data "
            f"mrcide/privateer-client:{cfg.tag} "
            "rsync -av --delete alice:/privateer/volumes/bob/data/ "
            "/privateer/volumes/data/"
        )
        assert cmd in lines


def test_can_run_restore(monkeypatch, managed_docker):
    mock_run = MagicMock()
    monkeypatch.setattr(
        privateer.restore, "run_container_with_command", mock_run
    )
    with vault_dev.Server(export_token=True) as server:
        cfg = read_config("example/simple.json")
        cfg.vault.url = server.url()
        vol = managed_docker("volume")
        cfg.clients[0].key_volume = vol
        keygen_all(cfg)
        configure(cfg, "bob")
        restore(cfg, "bob", "data")

        image = f"mrcide/privateer-client:{cfg.tag}"
        command = [
            "rsync",
            "-av",
            "--delete",
            "alice:/privateer/volumes/bob/data/",
            "/privateer/volumes/data/",
        ]
        mounts = [
            docker.types.Mount(
                "/privateer/keys", vol, type="volume", read_only=True
            ),
            docker.types.Mount(
                "/privateer/volumes/data",
                "data",
                type="volume",
                read_only=False,
            ),
        ]
        assert mock_run.call_count == 1
        assert mock_run.call_args == call(
            "Restore", image, command=command, mounts=mounts
        )


def test_restore_from_local_volume(capsys, managed_docker):
    with vault_dev.Server(export_token=True) as server:
        cfg = read_config("example/local.json")
        cfg.vault.url = server.url()
        vol = managed_docker("volume")
        cfg.clients[0].key_volume = vol
        keygen_all(cfg)
        configure(cfg, "bob")
        capsys.readouterr()  # flush previous output
        restore(cfg, "bob", "other", dry_run=True)
        out = capsys.readouterr()
        lines = out.out.strip().split("\n")
        assert "Command to manually run restore:" in lines
        cmd = (
            "  docker run --rm "
            f"-v {vol}:/privateer/keys:ro -v other:/privateer/volumes/other "
            f"mrcide/privateer-client:{cfg.tag} "
            "rsync -av --delete alice:/privateer/local/other/ "
            "/privateer/volumes/other/"
        )
        assert cmd in lines


def test_restore_from_alternative_source(capsys, managed_docker):
    with vault_dev.Server(export_token=True) as server:
        cfg = read_config("example/complex.json")
        cfg.vault.url = server.url()
        vol_bob = managed_docker("volume")
        vol_dan = managed_docker("volume")
        cfg.clients[0].key_volume = vol_bob
        cfg.clients[1].key_volume = vol_dan
        keygen_all(cfg)
        configure(cfg, "bob")
        configure(cfg, "dan")
        capsys.readouterr()  # flush previous output

        # Data from carol, put there by bob, coming down to dan
        restore(cfg, "dan", "data", source="bob", server="carol", dry_run=True)
        out = capsys.readouterr()
        lines = out.out.strip().split("\n")
        assert "Command to manually run restore:" in lines
        cmd = (
            "  docker run --rm "
            f"-v {vol_dan}:/privateer/keys:ro -v data:/privateer/volumes/data "
            f"mrcide/privateer-client:{cfg.tag} "
            "rsync -av --delete carol:/privateer/volumes/bob/data/ "
            "/privateer/volumes/data/"
        )
        assert cmd in lines

        # Data from carol, local volume, coming down to dan
        restore(cfg, "dan", "other", source=None, server="carol", dry_run=True)
        out = capsys.readouterr()
        lines = out.out.strip().split("\n")
        assert "Command to manually run restore:" in lines
        cmd = (
            "  docker run --rm "
            f"-v {vol_dan}:/privateer/keys:ro "
            "-v other:/privateer/volumes/other "
            f"mrcide/privateer-client:{cfg.tag} "
            "rsync -av --delete carol:/privateer/local/other/ "
            "/privateer/volumes/other/"
        )
        assert cmd in lines
