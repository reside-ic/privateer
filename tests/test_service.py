from unittest.mock import MagicMock, Mock, call

import pytest

import docker
import privateer.service
from privateer.service import (
    service_command,
    service_start,
    service_status,
    service_stop,
)


def test_can_create_command():
    base = ["docker", "run", "--rm", "-d", "--name", "nm"]
    assert service_command("img", "nm") == [*base, "img"]
    assert service_command("img", "nm", command=["a", "b"]) == [
        *base,
        "img",
        "a",
        "b",
    ]
    mounts = [docker.types.Mount("/dest", "vol", type="volume", read_only=True)]
    assert service_command("img", "nm", mounts=mounts) == [
        *base,
        "-v",
        "vol:/dest:ro",
        "img",
    ]
    assert service_command("img", "nm", ports={"22/tcp": 10022}) == [
        *base,
        "-p",
        "10022:22",
        "img",
    ]


def test_can_launch_container(monkeypatch):
    mock_docker = MagicMock()
    client = mock_docker.from_env.return_value
    mock_exists = MagicMock()
    mock_exists.return_value = False
    mock_ensure_image = MagicMock()
    mounts = Mock()
    ports = Mock()
    command = Mock()
    monkeypatch.setattr(privateer.service, "docker", mock_docker)
    monkeypatch.setattr(privateer.service, "container_exists", mock_exists)
    monkeypatch.setattr(privateer.service, "ensure_image", mock_ensure_image)
    service_start(
        "alice", "nm", "img", mounts=mounts, ports=ports, command=command
    )
    assert mock_exists.call_count == 1
    assert mock_exists.call_args == call("nm")
    assert mock_ensure_image.call_count == 1
    assert mock_ensure_image.call_args == call("img")
    assert mock_docker.from_env.call_count == 1
    assert client.containers.run.call_count == 1
    assert client.containers.run.call_args == call(
        "img",
        auto_remove=True,
        detach=True,
        name="nm",
        mounts=mounts,
        ports=ports,
        command=command,
    )


def test_throws_if_container_already_exists(monkeypatch):
    mock_exists = MagicMock()
    mock_exists.return_value = True
    monkeypatch.setattr(privateer.service, "container_exists", mock_exists)
    msg = "Container 'nm' for 'alice' already running"
    with pytest.raises(Exception, match=msg):
        service_start("alice", "nm", "img")
    assert mock_exists.call_count == 1
    mock_exists.assert_called_with("nm")


def test_returns_cmd_even_if_container_already_exists(capsys, monkeypatch):
    mock_exists = MagicMock()
    mock_exists.return_value = True
    monkeypatch.setattr(privateer.service, "container_exists", mock_exists)
    service_start("alice", "nm", "img", dry_run=True)
    expected = service_command("img", "nm")
    out = capsys.readouterr().out
    assert " ".join(expected) in out
    assert mock_exists.call_count == 0


def test_can_stop_service(monkeypatch, capsys):
    mock_container = MagicMock()
    mock_container.status = "running"
    mock_container_if_exists = MagicMock(return_value=mock_container)
    monkeypatch.setattr(
        privateer.service,
        "container_if_exists",
        mock_container_if_exists,
    )

    service_stop("alice", "nm")
    assert mock_container_if_exists.call_count == 1
    assert mock_container_if_exists.call_args == call("nm")
    assert mock_container.stop.call_count == 1
    assert mock_container.stop.call_args == call()
    assert capsys.readouterr().out == ""

    mock_container.status = "exited"
    service_stop("alice", "nm")
    assert mock_container_if_exists.call_count == 2
    assert mock_container.stop.call_count == 1
    assert capsys.readouterr().out == ""

    mock_container_if_exists.return_value = None
    service_stop("alice", "nm")
    assert mock_container_if_exists.call_count == 3
    assert mock_container.stop.call_count == 1
    assert (
        capsys.readouterr().out == "Container 'nm' for 'alice' does not exist\n"
    )


def test_can_get_service_status(monkeypatch, capsys):
    mock_container = MagicMock()
    mock_container.status = "running"
    mock_container_if_exists = MagicMock(return_value=mock_container)
    monkeypatch.setattr(
        privateer.service,
        "container_if_exists",
        mock_container_if_exists,
    )

    service_status("nm")
    assert mock_container_if_exists.call_count == 1
    assert mock_container_if_exists.call_args == call("nm")
    assert capsys.readouterr().out == "running\n"

    mock_container.status = "exited"
    service_status("nm")
    assert mock_container_if_exists.call_count == 2
    assert capsys.readouterr().out == "exited\n"

    mock_container_if_exists.return_value = None
    service_status("nm")
    assert mock_container_if_exists.call_count == 3
    assert capsys.readouterr().out == "not running\n"
