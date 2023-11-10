import pytest
import vault_dev

import docker
from privateer.check import check
from privateer.config import read_config
from privateer.configure import configure
from privateer.keys import keygen_all
from privateer.util import string_from_volume
from privateer.yacron import generate_yacron_yaml


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


def test_can_write_schedule_for_client(managed_docker):
    with vault_dev.Server(export_token=True) as server:
        cfg = read_config("example/schedule.json")
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
            "yacron.yml",
        }
        schedule = string_from_volume(vol, "yacron.yml")
        expected = generate_yacron_yaml(cfg, "bob")
        assert schedule == "".join([x + "\n" for x in expected])
