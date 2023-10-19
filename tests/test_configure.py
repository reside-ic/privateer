import pytest
import vault_dev

import docker
from privateer2.config import read_config
from privateer2.configure import configure
from privateer2.keys import check, keygen_all
from privateer2.util import string_from_volume


def test_can_unpack_keys_for_server(managed_docker):
    with vault_dev.Server(export_token=True) as server:
        cfg = read_config("example/simple.json")
        cfg.vault.url = server.url()
        vol = managed_docker("volume")
        cfg.servers[0].key_volume = vol
        keygen_all(cfg)
        configure(cfg, "alice")
        client = docker.from_env()
        mounts = [docker.types.Mount("/keys", vol, type="volume")]
        name = managed_docker("container")
        res = client.containers.run(
            "alpine",
            mounts=mounts,
            command=["ls", "/keys"],
            name=name,
        )
        assert set(res.decode("UTF-8").strip().split("\n")) == {
            "authorized_keys",
            "id_rsa",
            "id_rsa.pub",
            "name",
        }
        assert string_from_volume(vol, "name") == "alice"


def test_can_unpack_keys_for_client(managed_docker):
    with vault_dev.Server(export_token=True) as server:
        cfg = read_config("example/simple.json")
        cfg.vault.url = server.url()
        vol = managed_docker("volume")
        cfg.clients[0].key_volume = vol
        keygen_all(cfg)
        configure(cfg, "bob")
        client = docker.from_env()
        mounts = [docker.types.Mount("/keys", vol, type="volume")]
        name = managed_docker("container")
        res = client.containers.run(
            "alpine",
            mounts=mounts,
            command=["ls", "/keys"],
            name=name,
        )
        assert set(res.decode("UTF-8").strip().split("\n")) == {
            "known_hosts",
            "id_rsa",
            "id_rsa.pub",
            "name",
            "config",
        }
        assert string_from_volume(vol, "name") == "bob"
        assert check(cfg, "bob").key_volume == vol
        msg = "Configuration is for 'bob', not 'alice'"
        cfg.servers[0].key_volume = vol
        with pytest.raises(Exception, match=msg):
            check(cfg, "alice")
