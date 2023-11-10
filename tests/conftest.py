import pytest
import vault_dev

from privateer.util import (
    container_if_exists,
    match_value,
    rand_str,
    volume_if_exists,
)

vault_dev.ensure_installed()


@pytest.fixture
def managed_docker():
    created = {"container": [], "volume": []}

    def _new(what, *, prefix="privateer_test"):
        match_value(what, ["container", "volume"], "what")
        name = f"{prefix}_{rand_str()}"
        created[what].append(name)
        return name

    yield _new

    for name in created["container"]:
        container = container_if_exists(name)
        if container:
            container.remove()
    for name in created["volume"]:
        volume = volume_if_exists(name)
        if volume:
            volume.remove()
