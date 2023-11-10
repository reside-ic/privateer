import pytest
import vault_dev

from privateer.config import _check_config, find_source, read_config


def test_can_read_config():
    cfg = read_config("example/simple.json")
    assert len(cfg.servers) == 1
    assert cfg.servers[0].name == "alice"
    assert cfg.servers[0].hostname == "alice.example.com"
    assert cfg.servers[0].port == 10022
    assert len(cfg.clients) == 1
    assert cfg.clients[0].name == "bob"
    assert cfg.clients[0].backup == ["data"]
    assert len(cfg.volumes) == 1
    assert cfg.volumes[0].name == "data"
    assert cfg.vault.url == "http://localhost:8200"
    assert cfg.vault.prefix == "/privateer"
    assert cfg.list_servers() == ["alice"]
    assert cfg.list_clients() == ["bob"]
    assert cfg.clients[0].schedule is None


def test_can_create_vault_client():
    cfg = read_config("example/simple.json")
    with vault_dev.Server(export_token=True) as server:
        cfg.vault.url = server.url()
        client = cfg.vault.client()
        assert client.is_authenticated()


# These are annoying to setup, the rest just run the validation manually:
def test_validation_is_run_on_load(tmp_path):
    path = tmp_path / "privateer.json"
    with path.open("w") as f:
        f.write(
            """{
    "servers": [
        {
            "name": "alice",
            "hostname": "alice.example.com",
            "port": 10022,
            "key_volume": "privateer_keys",
            "data_volume": "privateer_data",
            "container": "privateer_server"
        }
    ],
    "clients": [
        {
            "name": "alice",
            "backup": ["data"],
            "restore": ["data", "other"]
        }
    ],
    "volumes": [
        {
            "name": "data"
        }
    ],
    "vault": {
        "url": "http://localhost:8200",
        "prefix": "/secret/privateer"
    }
}"""
        )
    msg = "Invalid machine listed as both a client and a server: 'alice'"
    with pytest.raises(Exception, match=msg):
        read_config(path)


def test_machines_cannot_be_duplicated():
    cfg = read_config("example/simple.json")
    cfg.clients = cfg.clients + cfg.clients
    with pytest.raises(Exception, match="Duplicated elements in clients"):
        _check_config(cfg)
    cfg.servers = cfg.servers + cfg.servers
    with pytest.raises(Exception, match="Duplicated elements in servers"):
        _check_config(cfg)


def test_machines_cannot_be_client_and_server():
    cfg = read_config("example/simple.json")
    tmp = cfg.clients[0].model_copy()
    tmp.name = "alice"
    cfg.clients.append(tmp)
    msg = "Invalid machine listed as both a client and a server: 'alice'"
    with pytest.raises(Exception, match=msg):
        _check_config(cfg)


def test_backup_volumes_are_known():
    cfg = read_config("example/simple.json")
    cfg.clients[0].backup.append("other")
    msg = "Client 'bob' backs up unknown volume 'other'"
    with pytest.raises(Exception, match=msg):
        _check_config(cfg)


def test_local_volumes_cannot_be_backed_up():
    cfg = read_config("example/simple.json")
    cfg.volumes[0].local = True
    msg = "Client 'bob' backs up local volume 'data'"
    with pytest.raises(Exception, match=msg):
        _check_config(cfg)


def test_can_find_appropriate_source():
    cfg = read_config("example/simple.json")
    tmp = cfg.clients[0].model_copy()
    tmp.name = "carol"
    cfg.clients.append(tmp)
    assert find_source(cfg, "data", "bob") == "bob"
    assert find_source(cfg, "data", "carol") == "carol"
    msg = "Invalid source 'alice': valid options: 'bob', 'carol'"
    with pytest.raises(Exception, match=msg):
        find_source(cfg, "data", "alice")
    with pytest.raises(Exception, match="Unknown volume 'unknown'"):
        find_source(cfg, "unknown", "alice")


def test_can_find_appropriate_source_if_local():
    cfg = read_config("example/simple.json")
    cfg.volumes[0].local = True
    assert find_source(cfg, "data", None) is None
    msg = "'data' is a local source, so 'source' must be empty"
    with pytest.raises(Exception, match=msg):
        find_source(cfg, "data", "bob")
    with pytest.raises(Exception, match=msg):
        find_source(cfg, "data", "local")


def test_can_strip_leading_secret_from_path():
    cfg = read_config("example/simple.json")

    cfg.vault.prefix = "/secret/my/path"
    _check_config(cfg)
    assert cfg.vault.prefix == "/my/path"

    cfg.vault.prefix = "/my/path"
    _check_config(cfg)
    assert cfg.vault.prefix == "/my/path"


def test_can_read_config_with_schedule():
    cfg = read_config("example/schedule.json")
    schedule = cfg.clients[0].schedule
    assert schedule.container == "privateer_scheduler"
    assert schedule.port == 8080
    assert len(schedule.jobs) == 2
    assert schedule.jobs[0].server == "alice"
    assert schedule.jobs[0].volume == "data1"
    assert schedule.jobs[0].schedule == "@daily"
    assert schedule.jobs[1].server == "alice"
    assert schedule.jobs[1].volume == "data2"
    assert schedule.jobs[1].schedule == "@weekly"


def test_can_validate_schedule_goes_to_correct_server():
    cfg = read_config("example/schedule.json")
    cfg.clients[0].schedule.jobs[1].server = "carol"
    msg = "Client 'bob' scheduling backup to unknown server 'carol'"
    with pytest.raises(Exception, match=msg):
        _check_config(cfg)


def test_can_validate_schedule_backs_up_correct_volume():
    cfg = read_config("example/schedule.json")
    cfg.clients[0].backup = ["data1"]
    msg = (
        "Client 'bob' scheduling backup of volume 'data2', "
        "which it does not back up"
    )
    with pytest.raises(Exception, match=msg):
        _check_config(cfg)
