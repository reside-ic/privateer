import shutil
from unittest.mock import call

from click.testing import CliRunner

from privateer import cli2
from privateer.config import read_config
from privateer.configure import write_identity


def test_can_run_keygen(tmp_path, mocker):
    mocker.patch("privateer.cli2.keygen_all")
    mocker.patch("privateer.cli2.keygen")
    runner = CliRunner()
    shutil.copy("example/simple.json", tmp_path / "privateer.json")

    res = runner.invoke(cli2.cli_keygen, ["--path", tmp_path])
    cfg = read_config(tmp_path / "privateer.json")
    assert res.exit_code == 0
    assert cli2.keygen.call_count == 1
    assert cli2.keygen.mock_calls[0] == call(cfg, None)

    res = runner.invoke(cli2.cli_keygen, ["--path", tmp_path, "alice"])
    cfg = read_config(tmp_path / "privateer.json")
    assert res.exit_code == 0
    assert cli2.keygen.call_count == 2
    assert cli2.keygen.mock_calls[1] == call(cfg, "alice")

    res = runner.invoke(cli2.cli_keygen, ["--path", tmp_path, "--all"])
    cfg = read_config(tmp_path / "privateer.json")
    assert res.exit_code == 0
    assert cli2.keygen_all.call_count == 1
    assert cli2.keygen_all.mock_calls[0] == call(cfg)


def test_can_run_configure(tmp_path, mocker):
    mocker.patch("privateer.cli2.configure")
    runner = CliRunner()
    shutil.copy("example/simple.json", tmp_path / "privateer.json")

    res = runner.invoke(cli2.cli_configure, ["--path", tmp_path, "alice"])
    cfg = read_config(tmp_path / "privateer.json")

    assert res.exit_code == 0
    dest = tmp_path / ".privateer_identity"
    assert dest.exists()
    with dest.open() as f:
        assert f.read().strip() == "alice"

    assert cli2.configure.call_count == 1
    assert cli2.configure.mock_calls[0] == call(cfg, "alice")


def test_can_call_check(tmp_path, mocker):
    mocker.patch("privateer.cli2.check")
    runner = CliRunner()
    shutil.copy("example/simple.json", tmp_path / "privateer.json")
    write_identity(tmp_path, "alice")

    cfg = read_config(tmp_path / "privateer.json")

    res = runner.invoke(cli2.cli_check, ["--path", tmp_path, "--connection"])
    assert res.exit_code == 0
    assert cli2.check.call_count == 1
    assert cli2.check.mock_calls[0] == call(
        cfg=cfg, name="alice", connection=True
    )


def test_can_call_backup(tmp_path, mocker):
    mocker.patch("privateer.cli2.backup")
    runner = CliRunner()
    shutil.copy("example/simple.json", tmp_path / "privateer.json")
    write_identity(tmp_path, "alice")
    cfg = read_config(tmp_path / "privateer.json")

    res = runner.invoke(cli2.cli_backup, ["--path", tmp_path, "data"])
    assert res.exit_code == 0
    assert cli2.backup.call_count == 1
    assert cli2.backup.mock_calls[0] == call(
        cfg=cfg, name="alice", volume="data", server=None, dry_run=False
    )


def test_can_call_restore(tmp_path, mocker):
    mocker.patch("privateer.cli2.restore")
    runner = CliRunner()
    shutil.copy("example/simple.json", tmp_path / "privateer.json")
    write_identity(tmp_path, "bob")
    cfg = read_config(tmp_path / "privateer.json")

    res = runner.invoke(cli2.cli_restore, ["--path", tmp_path, "data"])
    assert res.exit_code == 0
    assert cli2.restore.call_count == 1
    assert cli2.restore.mock_calls[0] == call(
        cfg=cfg,
        name="bob",
        volume="data",
        server=None,
        source=None,
        dry_run=False,
    )


def test_can_call_export_of_local_volume(mocker):
    mocker.patch("privateer.cli2.export_tar_local")
    runner = CliRunner()
    res = runner.invoke(cli2.cli_export, ["--source", "local", "data"])
    assert res.exit_code == 0
    assert cli2.export_tar_local.call_count == 1
    assert cli2.export_tar_local.mock_calls[0] == call(
        volume="data", to_dir=None, dry_run=False
    )


def test_can_export_a_volume(tmp_path, mocker):
    mocker.patch("privateer.cli2.export_tar")
    runner = CliRunner()
    shutil.copy("example/simple.json", tmp_path / "privateer.json")
    write_identity(tmp_path, "bob")
    cfg = read_config(tmp_path / "privateer.json")

    res = runner.invoke(cli2.cli_export, ["--path", tmp_path, "data"])
    assert res.exit_code == 0
    assert cli2.export_tar.call_count == 1
    assert cli2.export_tar.mock_calls[0] == call(
        cfg=cfg,
        name=None,
        volume="data",
        to_dir=None,
        source=None,
        dry_run=False,
    )


def test_can_import_a_volume(mocker):
    mocker.patch("privateer.cli2.import_tar")
    runner = CliRunner()

    res = runner.invoke(cli2.cli_import, ["file.tar", "data"])
    assert res.exit_code == 0
    assert cli2.import_tar.call_count == 1
    assert cli2.import_tar.mock_calls[0] == call(
        volume="data", tarfile="file.tar", dry_run=False
    )


def test_can_interact_with_server(tmp_path, mocker):
    mocker.patch("privateer.cli2.server_start")
    mocker.patch("privateer.cli2.server_stop")
    mocker.patch("privateer.cli2.server_status")
    runner = CliRunner()
    shutil.copy("example/simple.json", tmp_path / "privateer.json")
    write_identity(tmp_path, "alice")
    cfg = read_config(tmp_path / "privateer.json")

    res = runner.invoke(cli2.cli_server, ["--path", tmp_path, "start"])
    assert res.exit_code == 0
    assert cli2.server_start.call_count == 1
    assert cli2.server_start.mock_calls[0] == call(
        cfg=cfg, name=None, dry_run=False
    )

    res = runner.invoke(cli2.cli_server, ["--path", tmp_path, "status"])
    assert res.exit_code == 0
    assert cli2.server_status.call_count == 1
    assert cli2.server_status.mock_calls[0] == call(cfg=cfg, name=None)

    res = runner.invoke(cli2.cli_server, ["--path", tmp_path, "stop"])
    assert res.exit_code == 0
    assert cli2.server_stop.call_count == 1
    assert cli2.server_stop.mock_calls[0] == call(cfg=cfg, name=None)


def test_can_interact_with_schedule(tmp_path, mocker):
    mocker.patch("privateer.cli2.schedule_start")
    mocker.patch("privateer.cli2.schedule_stop")
    mocker.patch("privateer.cli2.schedule_status")
    runner = CliRunner()
    shutil.copy("example/simple.json", tmp_path / "privateer.json")
    write_identity(tmp_path, "alice")
    cfg = read_config(tmp_path / "privateer.json")

    res = runner.invoke(cli2.cli_schedule, ["--path", tmp_path, "start"])
    assert res.exit_code == 0
    assert cli2.schedule_start.call_count == 1
    assert cli2.schedule_start.mock_calls[0] == call(
        cfg=cfg, name=None, dry_run=False
    )

    res = runner.invoke(cli2.cli_schedule, ["--path", tmp_path, "status"])
    assert res.exit_code == 0
    assert cli2.schedule_status.call_count == 1
    assert cli2.schedule_status.mock_calls[0] == call(cfg=cfg, name=None)

    res = runner.invoke(cli2.cli_schedule, ["--path", tmp_path, "stop"])
    assert res.exit_code == 0
    assert cli2.schedule_stop.call_count == 1
    assert cli2.schedule_stop.mock_calls[0] == call(cfg=cfg, name=None)
