import datetime
import os
import os.path
import random
import re
import string
import tarfile
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import TypeVar

import docker
import tzlocal
from docker.models.containers import Container
from docker.models.volumes import Volume

T = TypeVar("T")


def unique(x: list[T]) -> list[T]:
    seen = set()
    ret = []
    for el in x:
        if el not in seen:
            ret.append(el)
            seen.add(el)
    return ret


def string_to_volume(
    text: str | list[str], volume: str, path: str | Path, **kwargs
) -> None:
    if isinstance(text, list):
        text = "".join(x + "\n" for x in text)
    ensure_image("alpine")
    dest = Path("/dest")
    mounts = [docker.types.Mount(str(dest), volume, type="volume")]
    cl = docker.from_env()
    container = cl.containers.create("alpine", mounts=mounts, detach=True)
    try:
        string_to_container(text, container, dest / path, **kwargs)
    finally:
        container.remove()


def string_from_volume(volume: str, path: str | Path) -> str:
    ensure_image("alpine")
    src = Path("/src")
    mounts = [docker.types.Mount(str(src), volume, type="volume")]
    cl = docker.from_env()
    container = cl.containers.create("alpine", mounts=mounts, detach=True)
    try:
        return string_from_container(container, str(src / path))
    finally:
        container.remove()


def string_to_container(
    text: str, container: Container, path: str | Path, **kwargs
) -> None:
    with simple_tar_string(text, os.path.basename(path), **kwargs) as tar:
        container.put_archive(os.path.dirname(path), tar)


def string_from_container(container: Container, path: str) -> str:
    return bytes_from_container(container, path).decode("utf-8")


def bytes_from_container(container: Container, path: str) -> bytes:
    stream, status = container.get_archive(path)
    try:
        fd, tmp = tempfile.mkstemp(text=False)
        with os.fdopen(fd, "wb") as f:
            for d in stream:
                f.write(d)
        with open(tmp, "rb") as f:
            t = tarfile.open(mode="r", fileobj=f)
            p = t.extractfile(os.path.basename(path))
            # Probably this needs more care, but I think that the None
            # path is effectively prevented by docker already
            return p.read()  # type: ignore
    finally:
        os.remove(tmp)


def set_permissions(mode=None, uid=None, gid=None):
    def ret(tarinfo):
        if mode is not None:
            tarinfo.mode = mode
        if uid is not None:
            tarinfo.uid = uid
        if gid is not None:
            tarinfo.gid = gid
        return tarinfo

    return ret


def simple_tar_string(text: str, name: str, **kwargs):
    data = bytes(text, "utf-8")
    try:
        fd, tmp = tempfile.mkstemp(text=True)
        with os.fdopen(fd, "wb") as f:
            f.write(data)
        return simple_tar(tmp, name, **kwargs)
    finally:
        os.remove(tmp)


def simple_tar(path: str, name: str, **kwargs):
    f = tempfile.NamedTemporaryFile()
    t = tarfile.open(mode="w", fileobj=f)
    abs_path = os.path.abspath(path)
    t.add(
        abs_path,
        arcname=name,
        recursive=False,
        filter=set_permissions(**kwargs),
    )
    t.close()
    f.seek(0)
    return f


@contextmanager
def transient_envvar(env: dict[str, str | None]) -> Iterator[None]:
    def _set_envvars(env):
        for k, v in env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    prev = {k: os.environ.get(k) for k in env.keys()}
    try:
        _set_envvars(env)
        yield
    finally:
        _set_envvars(prev)


def ensure_image(name: str) -> None:
    cl = docker.from_env()
    try:
        cl.images.get(name)
    except docker.errors.ImageNotFound:
        print(f"Pulling {name}")
        cl.images.pull(name)


def container_exists(name: str) -> bool:
    return bool(container_if_exists(name))


def container_if_exists(name: str) -> Container | None:
    try:
        return docker.from_env().containers.get(name)
    except docker.errors.NotFound:
        return None


def volume_exists(name: str) -> bool:
    return bool(volume_if_exists(name))


def volume_if_exists(name: str) -> Volume | None:
    try:
        return docker.from_env().volumes.get(name)
    except docker.errors.NotFound:
        return None


def rand_str(n: int = 8) -> str:
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=n))


def log_tail(container: Container, n: int) -> list[str]:
    logs = container.logs().decode("utf-8").strip().split("\n")
    if len(logs) > n:
        return [f"(ommitting {len(logs) - n} lines of logs)", *logs[-n:]]
    else:
        return logs


def mounts_str(mounts: list[docker.types.Mount] | None) -> list[str]:
    ret = []
    if mounts:
        for m in mounts:
            ret += mount_str(m)
    return ret


def mount_str(mount: docker.types.Mount) -> list[str]:
    ret = f"{mount['Source']}:{mount['Target']}"
    if mount["ReadOnly"]:
        ret += ":ro"
    return ["-v", ret]


# This could be improved, there are more formats possible here.
def ports_str(ports: dict[str, int] | None) -> list[str]:
    ret = []
    if ports:
        for k, v in ports.items():
            ret.append("-p")
            ret.append(f"{v}:{re.sub('/.+', '', k)}")
    return ret


def match_value(given: str | None, valid: list[str], name: str) -> str:
    if given is None:
        if len(valid) == 1:
            return valid[0]
        msg = f"Please provide a value for {name}"
        raise Exception(msg)
    if given not in valid:
        valid_str = ", ".join([f"'{x}'" for x in valid])
        msg = f"Invalid {name} '{given}': valid options: {valid_str}"
        raise Exception(msg)
    return given


def isotimestamp() -> str:
    now = datetime.datetime.now(tz=datetime.timezone.utc)
    return now.strftime("%Y%m%d-%H%M%S")


def take_ownership(filename, directory, *, command_only=False):  # tar
    uid = os.geteuid()
    gid = os.getegid()
    cl = docker.from_env()
    ensure_image("ubuntu")
    mounts = [docker.types.Mount("/src", directory, type="bind")]
    command = ["chown", f"{uid}.{gid}", filename]
    if command_only:
        return [
            "docker",
            "run",
            "--rm",
            *mounts_str(mounts),
            "-w",
            "/src",
            "ubuntu",
            *command,
        ]
    else:
        cl.containers.run(
            "ubuntu",
            mounts=mounts,
            working_dir="/src",
            command=command,
            remove=True,
        )


def run_container_with_command(display: str, image: str, **kwargs) -> None:
    ensure_image(image)
    client = docker.from_env()
    container = client.containers.run(image, **kwargs, detach=True)
    print(f"{display} command started. To stream progress, run:")
    print(f"  docker logs -f {container.name}")
    result = container.wait()
    if result["StatusCode"] == 0:
        print(f"{display} completed successfully! Container logs:")
        print("\n".join(log_tail(container, 10)))
        container.remove()
    else:
        print("An error occured! Container logs:")
        print("\n".join(log_tail(container, 20)))
        msg = f"{display} failed; see {container.name} logs for details"
        raise Exception(msg)


@contextmanager
def transient_working_directory(path: str | Path) -> Iterator[None]:
    origin = os.getcwd()
    try:
        os.chdir(path)
        yield
    finally:
        os.chdir(origin)


def current_timezone_name() -> str:
    return str(tzlocal.get_localzone())
