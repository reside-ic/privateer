import shutil
from unittest.mock import MagicMock, call

import pytest

import privateer.cli
from privateer.cli import (
    Call,
    _do_configure,
    _find_identity,
    _parse_argv,
    _parse_opts,
    _path_config,
    _show_version,
    main,
    pull,
)
from privateer.config import read_config
from privateer.util import transient_working_directory


def test_can_create_and_run_call():
    def f(a, b=1):
        return [a, b]

    call = Call(f, a=1, b=2)
    assert call.run() == [1, 2]


def test_can_parse_version():
    res = _parse_argv(["--version"])
    assert res.target == privateer.cli._show_version
    assert res.kwargs == {}


def test_can_parse_import():
    res = _parse_argv(["import", "--dry-run", "f", "v"])
    assert res.target == privateer.cli.import_tar
    assert res.kwargs == {"volume": "v", "tarfile": "f", "dry_run": True}
    assert not _parse_argv(["import", "f", "v"]).kwargs["dry_run"]
    with pytest.raises(Exception, match="Don't use '--path' with 'import'"):
        _parse_argv(["--path=privateer.json", "import", "f", "v"])
    with pytest.raises(Exception, match="Don't use '--as' with 'import'"):
        _parse_argv(["--as=alice", "import", "f", "v"])


def test_can_parse_keygen_all():
    res = _parse_argv(["keygen", "--path=example/simple.json", "--all"])
    assert res.target == privateer.cli.keygen_all
    assert res.kwargs == {"cfg": read_config("example/simple.json")}


def test_can_parse_keygen_one():
    res = _parse_argv(["keygen", "--path=example/simple.json", "alice"])
    assert res.target == privateer.cli.keygen
    assert res.kwargs == {
        "cfg": read_config("example/simple.json"),
        "name": "alice",
    }


def test_can_prevent_use_of_as_with_keygen():
    with pytest.raises(Exception, match="Don't use '--as' with 'keygen'"):
        _parse_argv(["keygen", "--path=example/local.json", "--as", "x", "y"])


def test_can_parse_configure():
    res = _parse_argv(["configure", "--path=example/simple.json", "alice"])
    assert res.target == privateer.cli._do_configure
    assert res.kwargs == {
        "cfg": read_config("example/simple.json"),
        "name": "alice",
        "root": "example",
    }


def test_can_parse_configure_without_explicit_path(tmp_path):
    shutil.copy("example/simple.json", tmp_path / "privateer.json")
    with transient_working_directory(tmp_path):
        res = _parse_argv(["configure", "alice"])
    assert res.target == privateer.cli._do_configure
    assert res.kwargs == {
        "cfg": read_config("example/simple.json"),
        "name": "alice",
        "root": "",
    }


def test_can_parse_pull():
    res = _parse_argv(["pull", "--path=example/simple.json"])
    assert res.target == privateer.cli.pull
    assert res.kwargs == {"cfg": read_config("example/simple.json")}


def test_can_parse_check(tmp_path):
    shutil.copy("example/simple.json", tmp_path / "privateer.json")
    with open(tmp_path / ".privateer_identity", "w") as f:
        f.write("alice\n")
    with transient_working_directory(tmp_path):
        res = _parse_argv(["check"])
    assert res.target == privateer.cli.check
    assert res.kwargs == {
        "cfg": read_config("example/simple.json"),
        "name": "alice",
        "connection": False,
    }
    path = str(tmp_path / "privateer.json")
    _parse_argv(["check", "--path", path])
    assert _parse_argv(["check", "--path", path]) == res
    assert _parse_argv(["check", "--path", path, "--as", "alice"]) == res
    res.kwargs["name"] = "bob"
    assert _parse_argv(["check", "--path", path, "--as", "bob"]) == res
    res.kwargs["connection"] = True
    assert (
        _parse_argv(["check", "--path", path, "--as", "bob", "--connection"])
        == res
    )


def test_can_parse_server_start(tmp_path):
    shutil.copy("example/simple.json", tmp_path / "privateer.json")
    with open(tmp_path / ".privateer_identity", "w") as f:
        f.write("alice\n")
    with transient_working_directory(tmp_path):
        res = _parse_argv(["server", "start"])
    assert res.target == privateer.cli.server_start
    assert res.kwargs == {
        "cfg": read_config("example/simple.json"),
        "name": "alice",
        "dry_run": False,
    }


def test_can_parse_server_status(tmp_path):
    shutil.copy("example/simple.json", tmp_path / "privateer.json")
    with open(tmp_path / ".privateer_identity", "w") as f:
        f.write("alice\n")
    with transient_working_directory(tmp_path):
        res = _parse_argv(["server", "status"])
    assert res.target == privateer.cli.server_status
    assert res.kwargs == {
        "cfg": read_config("example/simple.json"),
        "name": "alice",
    }


def test_can_parse_server_stop(tmp_path):
    shutil.copy("example/simple.json", tmp_path / "privateer.json")
    with open(tmp_path / ".privateer_identity", "w") as f:
        f.write("alice\n")
    with transient_working_directory(tmp_path):
        res = _parse_argv(["server", "stop"])
    assert res.target == privateer.cli.server_stop
    assert res.kwargs == {
        "cfg": read_config("example/simple.json"),
        "name": "alice",
    }


def test_can_parse_backup(tmp_path):
    shutil.copy("example/simple.json", tmp_path / "privateer.json")
    with open(tmp_path / ".privateer_identity", "w") as f:
        f.write("alice\n")
    with transient_working_directory(tmp_path):
        res = _parse_argv(["backup", "v"])
    assert res.target == privateer.cli.backup
    assert res.kwargs == {
        "cfg": read_config("example/simple.json"),
        "name": "alice",
        "volume": "v",
        "server": None,
        "dry_run": False,
    }


def test_can_parse_backup_with_server(tmp_path):
    shutil.copy("example/simple.json", tmp_path / "privateer.json")
    with open(tmp_path / ".privateer_identity", "w") as f:
        f.write("alice\n")
    with transient_working_directory(tmp_path):
        res = _parse_argv(["backup", "v", "--server", "alice"])
    assert res.target == privateer.cli.backup
    assert res.kwargs == {
        "cfg": read_config("example/simple.json"),
        "name": "alice",
        "volume": "v",
        "server": "alice",
        "dry_run": False,
    }


def test_can_parse_restore(tmp_path):
    shutil.copy("example/simple.json", tmp_path / "privateer.json")
    with open(tmp_path / ".privateer_identity", "w") as f:
        f.write("alice\n")
    with transient_working_directory(tmp_path):
        res = _parse_argv(["restore", "v"])
    assert res.target == privateer.cli.restore
    assert res.kwargs == {
        "cfg": read_config("example/simple.json"),
        "name": "alice",
        "volume": "v",
        "server": None,
        "source": None,
        "dry_run": False,
    }


def test_can_parse_complex_restore(tmp_path):
    shutil.copy("example/simple.json", tmp_path / "privateer.json")
    with open(tmp_path / ".privateer_identity", "w") as f:
        f.write("alice\n")
    with transient_working_directory(tmp_path):
        res = _parse_argv(["restore", "v", "--server=alice", "--source=bob"])
    assert res.target == privateer.cli.restore
    assert res.kwargs == {
        "cfg": read_config("example/simple.json"),
        "name": "alice",
        "volume": "v",
        "server": "alice",
        "source": "bob",
        "dry_run": False,
    }


def test_can_parse_export(tmp_path):
    shutil.copy("example/simple.json", tmp_path / "privateer.json")
    with open(tmp_path / ".privateer_identity", "w") as f:
        f.write("alice\n")
    with transient_working_directory(tmp_path):
        res = _parse_argv(["export", "v"])
    assert res.target == privateer.cli.export_tar
    assert res.kwargs == {
        "cfg": read_config("example/simple.json"),
        "name": "alice",
        "volume": "v",
        "to_dir": None,
        "source": None,
        "dry_run": False,
    }


def test_can_parse_local_export():
    res = _parse_argv(["export", "v", "--source=local"])
    assert res.target == privateer.cli.export_tar_local
    assert res.kwargs == {
        "volume": "v",
        "to_dir": None,
        "dry_run": False,
    }
    with pytest.raises(Exception, match="Don't use '--as'"):
        _parse_argv(["export", "v", "--source=local", "--as=bob"])
    with pytest.raises(Exception, match="Don't use '--path'"):
        _parse_argv(["export", "v", "--source=local", "--path=p"])


def test_error_if_unknown_identity(tmp_path):
    shutil.copy("example/simple.json", tmp_path / "privateer.json")
    msg = "Can't determine identity; did you forget to configure"
    with pytest.raises(Exception, match=msg):
        _find_identity(None, tmp_path)
    assert _find_identity("alice", tmp_path) == "alice"
    with open(tmp_path / ".privateer_identity", "w") as f:
        f.write("alice\n")
    assert _find_identity(None, tmp_path) == "alice"
    assert _find_identity("bob", tmp_path) == "bob"


def test_configuration_writes_identity(tmp_path, monkeypatch):
    shutil.copy("example/simple.json", tmp_path / "privateer.json")
    cfg = read_config("example/simple.json")
    mock_configure = MagicMock()
    monkeypatch.setattr(privateer.cli, "configure", mock_configure)
    _do_configure(cfg, "alice", str(tmp_path))
    assert tmp_path.joinpath(".privateer_identity").exists()
    assert _find_identity(None, str(tmp_path)) == "alice"
    mock_configure.assert_called_once_with(cfg, "alice")


def test_can_print_version(capsys):
    _show_version()
    out = capsys.readouterr()
    assert out.out == f"privateer {privateer.cli.about.__version__}\n"


def test_options_parsing_else_clause(tmp_path):
    class empty:  # noqa
        def __getitem__(self, name):
            return None

    shutil.copy("example/simple.json", tmp_path / "privateer.json")
    with open(tmp_path / ".privateer_identity", "w") as f:
        f.write("alice\n")
    with pytest.raises(Exception, match="Invalid cli call -- privateer bug"):
        with transient_working_directory(tmp_path):
            _parse_opts(empty())


def test_call_main(monkeypatch):
    mock_call = MagicMock()
    monkeypatch.setattr(privateer.cli, "_parse_argv", mock_call)
    main(["--version"])
    assert mock_call.call_count == 1
    assert mock_call.call_args == call(["--version"])
    assert mock_call.return_value.run.call_count == 1
    assert mock_call.return_value.run.call_args == call()


def test_run_pull(monkeypatch):
    cfg = read_config("example/simple.json")
    image_client = f"mrcide/privateer-client:{cfg.tag}"
    image_server = f"mrcide/privateer-server:{cfg.tag}"
    mock_docker = MagicMock()
    monkeypatch.setattr(privateer.cli, "docker", mock_docker)
    pull(cfg)
    assert mock_docker.from_env.call_count == 1
    client = mock_docker.from_env.return_value
    assert client.images.pull.call_count == 2
    assert client.images.pull.call_args_list[0] == call(image_client)
    assert client.images.pull.call_args_list[1] == call(image_server)


def test_clean_path(tmp_path):
    with pytest.raises(Exception, match="Did not find privateer configuration"):
        with transient_working_directory(str(tmp_path)):
            _path_config(None)
    with pytest.raises(Exception, match="Did not find privateer configuration"):
        _path_config(tmp_path)
    with pytest.raises(Exception, match="Did not find privateer configuration"):
        _path_config(tmp_path / "foo.json")
    with pytest.raises(Exception, match="Did not find privateer configuration"):
        _path_config("foo.json")
    shutil.copy("example/simple.json", tmp_path / "privateer.json")
    assert _path_config(str(tmp_path)) == str(tmp_path / "privateer.json")
    assert _path_config("example/simple.json") == "example/simple.json"
    with transient_working_directory(str(tmp_path)):
        assert _path_config(None) == "privateer.json"


def test_can_parse_schedule_start(tmp_path):
    shutil.copy("example/schedule.json", tmp_path / "privateer.json")
    with open(tmp_path / ".privateer_identity", "w") as f:
        f.write("bob\n")
    with transient_working_directory(tmp_path):
        res = _parse_argv(["schedule", "start"])
    assert res.target == privateer.cli.schedule_start
    assert res.kwargs == {
        "cfg": read_config("example/schedule.json"),
        "name": "bob",
        "dry_run": False,
    }


def test_can_parse_schedule_status(tmp_path):
    shutil.copy("example/schedule.json", tmp_path / "privateer.json")
    with open(tmp_path / ".privateer_identity", "w") as f:
        f.write("bob\n")
    with transient_working_directory(tmp_path):
        res = _parse_argv(["schedule", "status"])
    assert res.target == privateer.cli.schedule_status
    assert res.kwargs == {
        "cfg": read_config("example/schedule.json"),
        "name": "bob",
    }


def test_can_parse_schedule_stop(tmp_path):
    shutil.copy("example/schedule.json", tmp_path / "privateer.json")
    with open(tmp_path / ".privateer_identity", "w") as f:
        f.write("bob\n")
    with transient_working_directory(tmp_path):
        res = _parse_argv(["schedule", "stop"])
    assert res.target == privateer.cli.schedule_stop
    assert res.kwargs == {
        "cfg": read_config("example/schedule.json"),
        "name": "bob",
    }
