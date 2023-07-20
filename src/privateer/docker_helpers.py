# There is an annoyance with docker and the requests library, where
# when the http handle is reclaimed a warning is printed.  It makes
# the test log almost impossible to read.
#
# https://github.com/kennethreitz/requests/issues/1882#issuecomment-52281285
# https://github.com/kennethreitz/requests/issues/3912
#
# This little helper can be used with python's with statement as
#
#      with DockerClient() as cl:
#        cl.containers...
#
# and will close *most* unused handles on exit.  It's easier to look
# at than endless try/finally blocks everywhere.
import os
import tarfile
import tempfile

import docker


class DockerClient:
    def __enter__(self):
        self.client = docker.client.from_env()
        return self.client

    def __exit__(self, t, value, traceback):
        pass


def containers_matching(prefix):
    cl = docker.client.from_env()
    return [x for x in cl.containers.list() if x.name.startswith(prefix)]


def simple_tar(path, name):
    f = tempfile.NamedTemporaryFile()
    t = tarfile.open(mode="w", fileobj=f)
    abs_path = os.path.abspath(path)
    t.add(abs_path, arcname=name, recursive=False)
    t.close()
    f.seek(0)
    return f


def simple_tar_string(text, name):
    if type(text) == str:
        text = bytes(text, "utf-8")
    try:
        fd, tmp = tempfile.mkstemp(text=True)
        with os.fdopen(fd, "wb") as f:
            f.write(text)
        return simple_tar(tmp, name)
    finally:
        os.remove(tmp)


# The python docker client does not provide nice 'docker cp' wrappers
# (https://github.com/docker/docker-py/issues/1771) - so we have to
# roll our own.  These are a real pain to do "properly".  For example
# see
# https://github.com/richfitz/stevedore/blob/845587/R/docker_client_support.R#L943-L1020
#
# So this function assumes that the destination directory exists and
# dumps out text into a file in the container
def string_into_container(txt, container, path):
    with simple_tar_string(txt, os.path.basename(path)) as tar:
        container.put_archive(os.path.dirname(path), tar)


def string_from_container(container, path):
    return bytes_from_container(container, path).decode("utf-8")


def bytes_from_container(container, path):
    stream, status = container.get_archive(path)
    try:
        fd, tmp = tempfile.mkstemp(text=False)
        with os.fdopen(fd, "wb") as f:
            for d in stream:
                f.write(d)
        with open(tmp, "rb") as f:
            t = tarfile.open(mode="r", fileobj=f)
            p = t.extractfile(os.path.basename(path))
            return p.read()
    finally:
        os.remove(tmp)
