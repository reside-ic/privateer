import docker
from privateer.keys import keys_data
from privateer.util import string_to_volume
from privateer.yacron import generate_yacron_yaml


def configure(cfg, name):
    cl = docker.from_env()
    keys = keys_data(cfg, name)
    schedule = generate_yacron_yaml(cfg, name)
    vol = cfg.machine_config(name).key_volume
    cl.volumes.create(vol)
    print(f"Copying keypair for '{name}' to volume '{vol}'")
    string_to_volume(
        keys["public"], vol, "id_rsa.pub", uid=0, gid=0, mode=0o644
    )
    string_to_volume(keys["private"], vol, "id_rsa", uid=0, gid=0, mode=0o600)
    if keys["authorized_keys"]:
        print("Authorising public keys")
        string_to_volume(
            keys["authorized_keys"],
            vol,
            "authorized_keys",
            uid=0,
            gid=0,
            mode=0o600,
        )
    if keys["known_hosts"]:
        print("Recognising servers")
        string_to_volume(
            keys["known_hosts"], vol, "known_hosts", uid=0, gid=0, mode=0o600
        )
    if keys["config"]:
        print("Adding ssh config")
        string_to_volume(
            keys["config"], vol, "config", uid=0, gid=0, mode=0o600
        )
    if schedule:
        print("Adding yacron schedule")
        string_to_volume(schedule, vol, "yacron.yml", uid=0, gid=0)
    string_to_volume(name, vol, "name", uid=0, gid=0)
