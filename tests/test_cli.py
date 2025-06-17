import shutil
from unittest.mock import call

import pytest
from click.testing import CliRunner

from privateer import cli
from privateer.config import read_config
from privateer.configure import write_identity


def test_can_run_keygen(tmp_path, mocker):
    mocker.patch("privateer.cli.keygen_all")
    mocker.patch("privateer.cli.keygen")
    runner = CliRunner()
    shutil.copy("example/simple.json", tmp_path / "privateer.json")

    res = runner.invoke(cli.cli_keygen, ["--path", tmp_path])
    cfg = read_config(tmp_path / "privateer.json")
    assert res.exit_code == 0
    assert cli.keygen.call_count == 1
    assert cli.keygen.mock_calls[0] == call(cfg, None)

    res = runner.invoke(cli.cli_keygen, ["--path", tmp_path, "alice"])
    cfg = read_config(tmp_path / "privateer.json")
    assert res.exit_code == 0
    assert cli.keygen.call_count == 2
    assert cli.keygen.mock_calls[1] == call(cfg, "alice")

    res = runner.invoke(cli.cli_keygen, ["--path", tmp_path, "--all"])
    cfg = read_config(tmp_path / "privateer.json")
    assert res.exit_code == 0
    assert cli.keygen_all.call_count == 1
    assert cli.keygen_all.mock_calls[0] == call(cfg)


def test_disallow_both_name_and_all(tmp_path, mocker):
    mocker.patch("privateer.cli.keygen_all")
    mocker.patch("privateer.cli.keygen")
    runner = CliRunner()
    shutil.copy("example/simple.json", tmp_path / "privateer.json")

    res = runner.invoke(cli.cli_keygen, ["--path", tmp_path, "--all", "bob"])
    assert res.exit_code == 1
    assert type(res.exception) is RuntimeError
    assert "Don't provide 'name'" in str(res.exception)


def test_can_run_pull(tmp_path, mocker):
    mocker.patch("privateer.cli.docker")
    runner = CliRunner()
    shutil.copy("example/simple.json", tmp_path / "privateer.json")

    res = runner.invoke(cli.cli_pull, ["--path", tmp_path])
    assert res.exit_code == 0
    assert cli.docker.from_env.call_count == 1
    client = cli.docker.from_env.return_value
    assert client.images.pull.call_count == 2
    assert client.images.pull.mock_calls[0] == call(
        "mrcide/privateer-client:latest"
    )
    assert client.images.pull.mock_calls[1] == call(
        "mrcide/privateer-server:latest"
    )


def test_can_run_configure(tmp_path, mocker):
    mocker.patch("privateer.cli.configure")
    runner = CliRunner()
    shutil.copy("example/simple.json", tmp_path / "privateer.json")

    res = runner.invoke(cli.cli_configure, ["--path", tmp_path, "alice"])
    cfg = read_config(tmp_path / "privateer.json")

    assert res.exit_code == 0
    dest = tmp_path / ".privateer_identity"
    assert dest.exists()
    with dest.open() as f:
        assert f.read().strip() == "alice"

    assert cli.configure.call_count == 1
    assert cli.configure.mock_calls[0] == call(cfg, "alice")


def test_can_call_check(tmp_path, mocker):
    mocker.patch("privateer.cli.check")
    runner = CliRunner()
    shutil.copy("example/simple.json", tmp_path / "privateer.json")
    write_identity(tmp_path, "alice")

    cfg = read_config(tmp_path / "privateer.json")

    res = runner.invoke(cli.cli_check, ["--path", tmp_path, "--connection"])
    assert res.exit_code == 0
    assert cli.check.call_count == 1
    assert cli.check.mock_calls[0] == call(
        cfg=cfg, name="alice", connection=True
    )


def test_can_call_backup(tmp_path, mocker):
    mocker.patch("privateer.cli.backup")
    runner = CliRunner()
    shutil.copy("example/simple.json", tmp_path / "privateer.json")
    write_identity(tmp_path, "alice")
    cfg = read_config(tmp_path / "privateer.json")

    res = runner.invoke(cli.cli_backup, ["--path", tmp_path, "data"])
    assert res.exit_code == 0
    assert cli.backup.call_count == 1
    assert cli.backup.mock_calls[0] == call(
        cfg=cfg, name="alice", volume="data", server=None, dry_run=False
    )


def test_can_call_restore(tmp_path, mocker):
    mocker.patch("privateer.cli.restore")
    runner = CliRunner()
    shutil.copy("example/simple.json", tmp_path / "privateer.json")
    write_identity(tmp_path, "bob")
    cfg = read_config(tmp_path / "privateer.json")

    res = runner.invoke(cli.cli_restore, ["--path", tmp_path, "data"])
    assert res.exit_code == 0
    assert cli.restore.call_count == 1
    assert cli.restore.mock_calls[0] == call(
        cfg=cfg,
        name="bob",
        volume="data",
        server=None,
        source=None,
        to_volume=None,
        dry_run=False,
    )


def test_can_call_export_of_local_volume(mocker):
    mocker.patch("privateer.cli.export_tar_local")
    runner = CliRunner()
    res = runner.invoke(cli.cli_export, ["--source", "local", "data"])
    assert res.exit_code == 0
    assert cli.export_tar_local.call_count == 1
    assert cli.export_tar_local.mock_calls[0] == call(
        volume="data", to_dir=None, dry_run=False
    )


def test_can_export_a_volume(tmp_path, mocker):
    mocker.patch("privateer.cli.export_tar")
    runner = CliRunner()
    shutil.copy("example/simple.json", tmp_path / "privateer.json")
    write_identity(tmp_path, "bob")
    cfg = read_config(tmp_path / "privateer.json")

    res = runner.invoke(cli.cli_export, ["--path", tmp_path, "data"])
    assert res.exit_code == 0
    assert cli.export_tar.call_count == 1
    assert cli.export_tar.mock_calls[0] == call(
        cfg=cfg,
        name=None,
        volume="data",
        to_dir=None,
        source=None,
        dry_run=False,
    )


def test_can_import_a_volume(mocker):
    mocker.patch("privateer.cli.import_tar")
    runner = CliRunner()

    res = runner.invoke(cli.cli_import, ["file.tar", "data"])
    assert res.exit_code == 0
    assert cli.import_tar.call_count == 1
    assert cli.import_tar.mock_calls[0] == call(
        volume="data", tarfile="file.tar", dry_run=False
    )


def test_can_interact_with_server(tmp_path, mocker):
    mocker.patch("privateer.cli.server_start")
    mocker.patch("privateer.cli.server_stop")
    mocker.patch("privateer.cli.server_status")
    runner = CliRunner()
    shutil.copy("example/simple.json", tmp_path / "privateer.json")
    write_identity(tmp_path, "alice")
    cfg = read_config(tmp_path / "privateer.json")

    res = runner.invoke(cli.cli_server, ["--path", tmp_path, "start"])
    assert res.exit_code == 0
    assert cli.server_start.call_count == 1
    assert cli.server_start.mock_calls[0] == call(
        cfg=cfg, name=None, dry_run=False
    )

    res = runner.invoke(cli.cli_server, ["--path", tmp_path, "status"])
    assert res.exit_code == 0
    assert cli.server_status.call_count == 1
    assert cli.server_status.mock_calls[0] == call(cfg=cfg, name=None)

    res = runner.invoke(cli.cli_server, ["--path", tmp_path, "stop"])
    assert res.exit_code == 0
    assert cli.server_stop.call_count == 1
    assert cli.server_stop.mock_calls[0] == call(cfg=cfg, name=None)


def test_can_interact_with_schedule(tmp_path, mocker):
    mocker.patch("privateer.cli.schedule_start")
    mocker.patch("privateer.cli.schedule_stop")
    mocker.patch("privateer.cli.schedule_status")
    runner = CliRunner()
    shutil.copy("example/simple.json", tmp_path / "privateer.json")
    write_identity(tmp_path, "alice")
    cfg = read_config(tmp_path / "privateer.json")

    res = runner.invoke(cli.cli_schedule, ["--path", tmp_path, "start"])
    assert res.exit_code == 0
    assert cli.schedule_start.call_count == 1
    assert cli.schedule_start.mock_calls[0] == call(
        cfg=cfg, name=None, dry_run=False
    )

    res = runner.invoke(cli.cli_schedule, ["--path", tmp_path, "status"])
    assert res.exit_code == 0
    assert cli.schedule_status.call_count == 1
    assert cli.schedule_status.mock_calls[0] == call(cfg=cfg, name=None)

    res = runner.invoke(cli.cli_schedule, ["--path", tmp_path, "stop"])
    assert res.exit_code == 0
    assert cli.schedule_stop.call_count == 1
    assert cli.schedule_stop.mock_calls[0] == call(cfg=cfg, name=None)


def test_can_read_identity(tmp_path):
    path = tmp_path / ".privateer_identity"
    assert cli._find_identity("bob", tmp_path) == "bob"
    with pytest.raises(Exception, match="Can't determine identity"):
        cli._find_identity(None, tmp_path)
    with path.open("w") as f:
        f.write("alice\n")
    assert cli._find_identity(None, tmp_path) == "alice"
