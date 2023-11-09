import os
import re
import tarfile

import pytest

import docker
import privateer.util


def test_create_simple_tar_from_string():
    p = privateer.util.simple_tar_string("hello", "path")
    t = tarfile.open(fileobj=p)
    els = t.getmembers()
    assert len(els) == 1
    assert els[0].name == "path"
    assert els[0].uid == os.geteuid()
    assert els[0].gid == os.getegid()


def test_create_simple_tar_with_permissions():
    p = privateer.util.simple_tar_string(
        "hello", "path", uid=0, gid=0, mode=0o600
    )
    t = tarfile.open(fileobj=p)
    els = t.getmembers()
    assert len(els) == 1
    assert els[0].name == "path"
    assert els[0].uid == 0
    assert els[0].gid == 0
    assert els[0].mode == 0o600


def test_can_match_values():
    match_value = privateer.util.match_value
    assert match_value(None, "x", "nm") == "x"
    assert match_value("x", "x", "nm") == "x"
    assert match_value("x", ["x", "y"], "nm") == "x"
    with pytest.raises(Exception, match="Please provide a value for nm"):
        match_value(None, ["x", "y"], "nm")
    msg = "Invalid nm 'z': valid options: 'x', 'y'"
    with pytest.raises(Exception, match=msg):
        match_value("z", ["x", "y"], "nm")


def test_can_format_timestamp():
    assert re.match("^[0-9]{8}-[0-9]{6}", privateer.util.isotimestamp())


def test_can_pull_image_if_required():
    def image_exists(name):
        cl = docker.from_env()
        try:
            cl.images.get(name)
            return True
        except docker.errors.ImageNotFound:
            return False

    cl = docker.from_env()
    if image_exists("hello-world:latest"):
        cl.images.get("hello-world:latest").remove()  # pragma: no cover
    assert not image_exists("hello-world:latest")
    privateer.util.ensure_image("hello-world:latest")
    assert image_exists("hello-world:latest")


def test_can_tail_logs_from_container(managed_docker):
    privateer.util.ensure_image("alpine")
    name = managed_docker("container")
    command = ["seq", "1", "10"]
    cl = docker.from_env()
    cl.containers.run("alpine", name=name, command=command)
    assert privateer.util.log_tail(cl.containers.get(name), 5) == [
        "(ommitting 5 lines of logs)",
        "6",
        "7",
        "8",
        "9",
        "10",
    ]
    assert privateer.util.log_tail(cl.containers.get(name), 100) == [
        "1",
        "2",
        "3",
        "4",
        "5",
        "6",
        "7",
        "8",
        "9",
        "10",
    ]


def test_can_run_long_command(capsys, managed_docker):
    name = managed_docker("container")
    command = ["seq", "1", "3"]
    privateer.util.run_container_with_command(
        "Test", "alpine", name=name, command=command
    )
    out = capsys.readouterr().out
    lines = out.strip().split("\n")
    assert lines[0] == "Test command started. To stream progress, run:"
    assert lines[1] == f"  docker logs -f {name}"
    assert lines[2] == "Test completed successfully! Container logs:"
    assert lines[3:] == ["1", "2", "3"]


def test_can_run_failing_command(capsys, managed_docker):
    name = managed_docker("container")
    command = ["false"]
    msg = f"Test failed; see {name} logs for details"
    with pytest.raises(Exception, match=msg):
        privateer.util.run_container_with_command(
            "Test", "alpine", name=name, command=command
        )
    out = capsys.readouterr().out
    lines = out.strip().split("\n")
    assert lines[0] == "Test command started. To stream progress, run:"
    assert lines[1] == f"  docker logs -f {name}"
    assert lines[2] == "An error occured! Container logs:"


def test_can_detect_if_volume_exists(managed_docker):
    name = managed_docker("volume")
    cl = docker.from_env()
    cl.volumes.create(name)
    assert privateer.util.volume_exists(name)
    cl.volumes.get(name).remove()
    assert not privateer.util.volume_exists(name)


def test_can_take_ownership_of_a_file(tmp_path, managed_docker):
    cl = docker.from_env()
    mounts = [docker.types.Mount("/src", str(tmp_path), type="bind")]
    command = ["touch", "/src/newfile"]
    name = managed_docker("container")
    cl.containers.run("ubuntu", name=name, mounts=mounts, command=command)
    path = tmp_path / "newfile"
    info = os.stat(path)
    assert info.st_uid == 0
    assert info.st_gid == 0
    uid = os.geteuid()
    gid = os.getegid()
    cmd = privateer.util.take_ownership(
        "newfile", str(tmp_path), command_only=True
    )
    expected = [
        "docker",
        "run",
        "--rm",
        *privateer.util.mounts_str(mounts),
        "-w",
        "/src",
        "alpine",
        "chown",
        f"{uid}.{gid}",
        "newfile",
    ]
    assert cmd == expected
    privateer.util.take_ownership("newfile", str(tmp_path))
    info = os.stat(path)
    assert info.st_uid == uid
    assert info.st_gid == gid


def test_can_format_ports():
    ports_str = privateer.util.ports_str
    assert ports_str(None) == []
    assert ports_str({"22/tcp": 10022}) == ["-p", "10022:22"]
    assert ports_str({"22": 10022}) == ["-p", "10022:22"]


def test_can_test_if_container_exists(managed_docker):
    name = managed_docker("container")
    assert not privateer.util.container_exists(name)
    assert privateer.util.container_if_exists(name) is None
    privateer.util.ensure_image("alpine")
    cl = docker.from_env()
    container = cl.containers.create("alpine", name=name)
    assert privateer.util.container_exists(name)
    assert privateer.util.container_if_exists(name) == container


def test_can_copy_string_into_volume(managed_docker):
    vol = managed_docker("volume")
    privateer.util.string_to_volume("hello", vol, "test")
    assert privateer.util.string_from_volume(vol, "test") == "hello"
    privateer.util.string_to_volume(["hello", "world"], vol, "test")
    assert privateer.util.string_from_volume(vol, "test") == "hello\nworld\n"


def test_can_uniquify_list():
    assert privateer.util.unique([]) == []
    assert privateer.util.unique([1, 2, 3]) == [1, 2, 3]
    assert privateer.util.unique([3, 2, 1, 2, 3]) == [3, 2, 1]
