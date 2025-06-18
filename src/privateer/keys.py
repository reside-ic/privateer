import hvac
from cryptography.hazmat.primitives import serialization as crypto_serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from privateer.config import Config


def keygen(cfg: Config, name: str) -> None:
    _keygen(cfg, name, cfg.vault.client())


def keygen_all(cfg: Config) -> None:
    vault = cfg.vault.client()
    for name in cfg.list_servers() + cfg.list_clients():
        _keygen(cfg, name, vault)


def keys_data(cfg: Config, name: str) -> dict[str, str]:
    vault = cfg.vault.client()
    response = vault.secrets.kv.v1.read_secret(f"{cfg.vault.prefix}/{name}")
    ret = {
        "name": name,
        **response["data"],
        "authorized_keys": None,
        "known_hosts": None,
        "config": None,
    }
    if name in cfg.list_servers():
        keys = _get_pubkeys(vault, cfg.vault.prefix, cfg.list_clients())
        ret["authorized_keys"] = "".join([f"{v}\n" for v in keys.values()])
    if name in cfg.list_clients():
        keys = _get_pubkeys(vault, cfg.vault.prefix, cfg.list_servers())
        known_hosts = []
        config = []
        for s in cfg.servers:
            known_hosts.append(f"[{s.hostname}]:{s.port} {keys[s.name]}\n")
            config.append(f"Host {s.name}\n")
            config.append("  User root\n")
            config.append(f"  Port {s.port}\n")
            config.append(f"  HostName {s.hostname}\n")
        ret["known_hosts"] = "".join(known_hosts)
        ret["config"] = "".join(config)
    return ret


def _keygen(cfg: Config, name: str, vault: hvac.Client):
    data = _create_keypair()
    path = f"{cfg.vault.prefix}/{name}"
    # TODO: The docs are here:
    # https://hvac.readthedocs.io/en/stable/usage/secrets_engines/kv_v1.html
    # They do not indicate if this will error if the write fails though.
    print(f"Writing keypair for {name}")
    _r = vault.secrets.kv.v1.create_or_update_secret(path, secret=data)


def _get_pubkeys(
    vault: hvac.Client, prefix: str, nms: list[str]
) -> dict[str, str]:
    return {
        nm: vault.secrets.kv.v1.read_secret(f"{prefix}/{nm}")["data"]["public"]
        for nm in nms
    }


def _create_keypair() -> dict[str, str]:
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    private = key.private_bytes(
        crypto_serialization.Encoding.PEM,
        crypto_serialization.PrivateFormat.PKCS8,
        crypto_serialization.NoEncryption(),
    ).decode("UTF-8")

    public = (
        key.public_key()
        .public_bytes(
            crypto_serialization.Encoding.OpenSSH,
            crypto_serialization.PublicFormat.OpenSSH,
        )
        .decode("UTF-8")
    )

    return {"public": public, "private": private}
