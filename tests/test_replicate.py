import pytest
import vault_dev

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
            f"-v other:/privateer/local/other:ro "
            f"-v {vol}:/privateer/keys:ro "
            f"mrcide/privateer-client:{cfg.tag} "
            "rsync -av --delete /privateer/local/other "
            "carol:/privateer/local/other"
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
            f"-v privateer_data:/privateer/volumes:ro "
            f"-v {vol}:/privateer/keys:ro "
            f"mrcide/privateer-client:{cfg.tag} "
            "rsync -av --delete /privateer/volumes/bob/data "
            "carol:/privateer/volumes/bob/data"
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
