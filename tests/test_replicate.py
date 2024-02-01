from unittest.mock import MagicMock, call

import pytest
import vault_dev

import docker
import privateer.replicate
from privateer.config import read_config
from privateer.configure import configure
from privateer.keys import keygen_all
from privateer.replicate import replicate


def test_can_print_instructions_to_run_replication(capsys, managed_docker):
    with vault_dev.Server(export_token=True) as server:
        cfg = read_config("example/complex.json")
        cfg.vault.url = server.url()
        vol = managed_docker("volume")
        cfg.servers[0].key_volume = vol
        keygen_all(cfg)
        configure(cfg, "alice")
        capsys.readouterr()  # flush previous output
        replicate(cfg, "alice", "other", "carol", dry_run=True)
        out = capsys.readouterr()
        lines = out.out.strip().split("\n")
        assert "Command to manually run replication:" in lines
        cmd = (
            "  docker run --rm "
            f"-v {vol}:/privateer/keys:ro "
            "-v other:/privateer/local/other:ro "
            f"mrcide/privateer-client:{cfg.tag} "
            "rsync -av --delete /privateer/local/other "
            "carol:/privateer/local"
        )
        assert cmd in lines


def test_can_print_instructions_to_run_src_replication(capsys, managed_docker):
    with vault_dev.Server(export_token=True) as server:
        cfg = read_config("example/complex.json")
        cfg.vault.url = server.url()
        vol = managed_docker("volume")
        cfg.servers[0].key_volume = vol
        keygen_all(cfg)
        configure(cfg, "alice")
        capsys.readouterr()  # flush previous output
        replicate(cfg, "alice", "data", "carol", source="bob", dry_run=True)
        out = capsys.readouterr()
        lines = out.out.strip().split("\n")
        assert "Command to manually run replication:" in lines
        cmd = (
            "  docker run --rm "
            f"-v {vol}:/privateer/keys:ro "
            "-v privateer_alice_data:/privateer/volumes:ro "
            "mrcide/privateer-client:latest "
            "rsync -av --delete /privateer/volumes/bob/data "
            "carol:/privateer/volumes/bob"
        )
        assert cmd in lines


def test_prevent_impossible_replication(managed_docker):
    with vault_dev.Server(export_token=True) as server:
        cfg = read_config("example/complex.json")
        cfg.vault.url = server.url()
        vol = managed_docker("volume")
        cfg.servers[0].key_volume = vol
        keygen_all(cfg)
        configure(cfg, "alice")
        msg = "Can only replicate to servers, but 'bob' is a client"
        with pytest.raises(Exception, match=msg):
            replicate(cfg, "alice", "other", "bob")
        msg = "Can't replicate to ourselves \\('alice'\\)"
        with pytest.raises(Exception, match=msg):
            replicate(cfg, "alice", "other", "alice")
        configure(cfg, "bob")
        msg = "Can only replicate from servers, but 'bob' is a client"
        with pytest.raises(Exception, match=msg):
            replicate(cfg, "bob", "other", "carol")


def test_can_replicate_between_servers(managed_docker, monkeypatch):
    mock_run = MagicMock()
    monkeypatch.setattr(
        privateer.replicate, "run_container_with_command", mock_run
    )
    with vault_dev.Server(export_token=True) as server:
        cfg = read_config("example/complex.json")
        cfg.vault.url = server.url()
        vol_alice = managed_docker("volume")
        vol_carol = managed_docker("volume")
        vol_other = managed_docker("volume")
        cfg.servers[0].key_volume = vol_alice
        cfg.servers[1].key_volume = vol_carol
        cfg.volumes[1].name = vol_other
        keygen_all(cfg)
        configure(cfg, "alice")
        replicate(cfg, "alice", vol_other, "carol")
        image = f"mrcide/privateer-client:{cfg.tag}"
        command = [
            "rsync",
            "-av",
            "--delete",
            f"/privateer/local/{vol_other}",
            "carol:/privateer/local",
        ]
        mounts = [
            docker.types.Mount(
                "/privateer/keys", vol_alice, type="volume", read_only=True
            ),
            docker.types.Mount(
                f"/privateer/local/{vol_other}",
                vol_other,
                type="volume",
                read_only=True,
            ),
        ]
        assert mock_run.call_count == 1
        assert mock_run.call_args == call(
            "Replication", image, command=command, mounts=mounts
        )
