import tempfile

from src.privateer.config import PrivateerConfig
from src.privateer.docker_helpers import DockerClient
from src.privateer.schedule import schedule_backups, cancel_scheduled_backups


def test_schedules():
    cfg = PrivateerConfig("config")
    host = cfg.get_host("test")
    host.path = tempfile.mkdtemp()
    schedule_backups(host, cfg.targets)
    with DockerClient() as cl:
        privateer_containers = [c for c in cl.containers.list() if c.name.startswith("privateer")]
        assert len(privateer_containers) == 1
        cancel_scheduled_backups()
        privateer_containers = [c for c in cl.containers.list() if c.name.startswith("privateer")]
        assert len(privateer_containers) == 0
