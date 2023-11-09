import os
import tarfile
from unittest.mock import MagicMock, call

import pytest
import vault_dev

import docker
import privateer.tar
import privateer.util
from privateer.config import read_config
from privateer.configure import configure
from privateer.keys import keygen_all
from privateer.tar import export_tar, export_tar_local, import_tar


def test_can_print_instructions_for_exporting_local_vol(managed_docker, capsys):
    vol = managed_docker("volume")
    privateer.util.string_to_volume("hello", vol, "test")
    path = export_tar_local(vol, dry_run=True)
    out = capsys.readouterr()
    lines = out.out.strip().split("\n")
    assert "Command to manually run export:" in lines
    assert "(pay attention to the final '.' in the above command!)" in lines
    cmd = (
        f"  docker run --rm "
        f"-v {os.getcwd()}:/export -v {vol}:/privateer:ro "
        f"-w /privateer ubuntu tar -cpvf /export/{os.path.basename(path)} ."
    )
    assert cmd in lines


def test_can_export_local_volume(tmp_path, managed_docker):
    vol = managed_docker("volume")
    privateer.util.string_to_volume("hello", vol, "test")
    path = export_tar_local(vol, to_dir=tmp_path)
    assert len(os.listdir(tmp_path)) == 1
    assert os.listdir(tmp_path)[0] == os.path.basename(path)
    with tarfile.open(path, "r") as f:
        assert f.getnames() == [".", "./test"]


def test_can_print_instructions_for_export_volume(managed_docker, capsys):
    with vault_dev.Server(export_token=True) as server:
        cfg = read_config("example/simple.json")
        cfg.vault.url = server.url()
        vol_keys = managed_docker("volume")
        vol_data = managed_docker("volume")
        name = managed_docker("container")
        cfg.servers[0].key_volume = vol_keys
        cfg.servers[0].data_volume = vol_data
        cfg.servers[0].container = name
        keygen_all(cfg)
        configure(cfg, "alice")
        capsys.readouterr()
        path = export_tar(cfg, "alice", "data", dry_run=True)
    out = capsys.readouterr()
    lines = out.out.strip().split("\n")
    assert "Command to manually run export:" in lines
    assert "(pay attention to the final '.' in the above command!)" in lines
    cmd = (
        f"  docker run --rm "
        f"-v {os.getcwd()}:/export -v {vol_data}:/privateer:ro "
        "-w /privateer/bob/data "
        f"ubuntu tar -cpvf /export/{os.path.basename(path)} ."
    )
    assert cmd in lines


def test_can_export_managed_volume(monkeypatch, managed_docker):
    mock_tar_create = MagicMock()
    monkeypatch.setattr(privateer.tar, "_run_tar_create", mock_tar_create)
    with vault_dev.Server(export_token=True) as server:
        cfg = read_config("example/simple.json")
        cfg.vault.url = server.url()
        vol = managed_docker("volume")
        cfg.servers[0].key_volume = managed_docker("volume")
        cfg.servers[0].data_volume = vol
        cfg.servers[0].container = managed_docker("container")
        keygen_all(cfg)
        configure(cfg, "alice")
        path = export_tar(cfg, "alice", "data")
    assert path == mock_tar_create.return_value
    assert mock_tar_create.call_count == 1
    call_args = mock_tar_create.call_args
    path = os.path.abspath("")
    mounts = [
        docker.types.Mount("/export", path, type="bind"),
        docker.types.Mount("/privateer", vol, type="volume", read_only=True),
    ]
    tarfile = call_args[0][3]
    src = "/privateer/bob/data"
    assert call_args == call(mounts, src, path, tarfile, False)


def test_can_export_local_managed_volume(monkeypatch, managed_docker):
    mock_tar_local = MagicMock()
    mock_tar_create = MagicMock()
    monkeypatch.setattr(privateer.tar, "_run_tar_create", mock_tar_create)
    monkeypatch.setattr(privateer.tar, "export_tar_local", mock_tar_local)
    with vault_dev.Server(export_token=True) as server:
        cfg = read_config("example/local.json")
        cfg.vault.url = server.url()
        vol_keys = managed_docker("volume")
        vol_data = managed_docker("volume")
        vol_other = managed_docker("volume")
        name = managed_docker("container")
        cfg.servers[0].key_volume = vol_keys
        cfg.servers[0].data_volume = vol_data
        cfg.servers[0].container = name
        cfg.volumes[1].name = vol_other
        keygen_all(cfg)
        configure(cfg, "alice")
    path = export_tar(cfg, "alice", vol_other)
    assert mock_tar_create.call_count == 0
    assert mock_tar_local.call_count == 1
    assert mock_tar_local.call_args == call(
        vol_other, to_dir=None, dry_run=False
    )
    assert path == mock_tar_local.return_value


def test_throw_if_local_volume_does_not_exist(managed_docker):
    vol = managed_docker("volume")
    msg = f"Volume '{vol}' does not exist"
    with pytest.raises(Exception, match=msg):
        export_tar_local(vol)


def test_throw_if_volume_does_not_exist(managed_docker):
    with vault_dev.Server(export_token=True) as server:
        cfg = read_config("example/simple.json")
        cfg.vault.url = server.url()
        vol = managed_docker("volume")
        cfg.servers[0].key_volume = managed_docker("volume")
        cfg.servers[0].data_volume = vol
        cfg.servers[0].container = managed_docker("container")
        keygen_all(cfg)
        configure(cfg, "alice")
    with pytest.raises(Exception, match="Unknown volume 'unknown'"):
        export_tar(cfg, "alice", "unknown")


def test_import_volume(managed_docker, tmp_path):
    src = managed_docker("volume")
    dest = managed_docker("volume")
    privateer.util.string_to_volume("hello", src, "test")
    path = export_tar_local(src, to_dir=tmp_path)
    import_tar(dest, path)
    assert privateer.util.string_from_volume(dest, "test") == "hello"


def test_instructions_to_import_volume(managed_docker, tmp_path, capsys):
    src = managed_docker("volume")
    dest = managed_docker("volume")
    privateer.util.string_to_volume("hello", src, "test")
    path = export_tar_local(src, to_dir=tmp_path)
    capsys.readouterr()
    import_tar(dest, path, dry_run=True)
    out = capsys.readouterr()
    lines = out.out.strip().split("\n")
    cmd = (
        f"  docker run --rm -v {path}:/src.tar:ro "
        f"-v {dest}:/privateer -w /privateer ubuntu tar -xvpf /src.tar"
    )
    assert "Command to manually run import:" in lines
    assert f"  docker volume create {dest}" in lines
    assert cmd in lines


def test_dont_import_into_existing_volume(tmp_path, managed_docker):
    dest = managed_docker("volume")
    docker.from_env().volumes.create(dest)
    path = str(tmp_path / "foo.tar")
    msg = f"Volume '{dest}' already exists, please delete first"
    with pytest.raises(Exception, match=msg):
        import_tar(dest, path)


def test_throw_if_tarfile_does_not_exist(tmp_path, managed_docker):
    dest = managed_docker("volume")
    path = str(tmp_path / "foo.tar")
    msg = f"Input file '{path}' does not exist"
    with pytest.raises(Exception, match=msg):
        import_tar(dest, path)
