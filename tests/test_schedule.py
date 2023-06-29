from src.privateer.config import PrivateerConfig
from src.privateer.schedule import schedule_backup


def test_schedules():
    cfg = PrivateerConfig("config")
    schedule_backup(cfg.get_host("test"), cfg.targets)
