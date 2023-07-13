import tempfile

from src.privateer.config import PrivateerConfig


def test_schedules():
    cfg = PrivateerConfig("config")
    host = cfg.get_host("test")
    host.path = tempfile.mkdtemp()
    # schedule_backup(host, cfg.targets)
