import vault_dev

from privateer.config import read_config
from privateer.keys import keygen, keygen_all, keys_data


def test_can_create_keys():
    with vault_dev.Server(export_token=True) as server:
        cfg = read_config("example/simple.json")
        cfg.vault.url = server.url()
        keygen(cfg, "alice")
        client = cfg.vault.client()
        response = client.secrets.kv.v1.read_secret("/privateer/alice")
        pair = response["data"]
        assert set(pair.keys()) == {"private", "public"}
        assert pair["public"].startswith("ssh-rsa")
        assert "PRIVATE KEY" in pair["private"]


def test_can_generate_server_keys_data():
    with vault_dev.Server(export_token=True) as server:
        cfg = read_config("example/simple.json")
        cfg.vault.url = server.url()
        keygen_all(cfg)
        dat = keys_data(cfg, "alice")
        assert dat["name"] == "alice"
        assert dat["known_hosts"] is None
        assert dat["authorized_keys"].startswith("ssh-rsa")


def test_can_generate_client_keys_data():
    with vault_dev.Server(export_token=True) as server:
        cfg = read_config("example/simple.json")
        cfg.vault.url = server.url()
        keygen_all(cfg)
        dat = keys_data(cfg, "bob")
        assert dat["name"] == "bob"
        assert dat["authorized_keys"] is None
        assert dat["known_hosts"].startswith(
            "[alice.example.com]:10022 ssh-rsa"
        )
