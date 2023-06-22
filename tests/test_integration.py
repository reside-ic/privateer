import os
import shutil

from src.privateer import cli
from src.privateer.config import PrivateerConfig


def test_backup_and_restore():
    cfg = PrivateerConfig("config")
    test = cfg.get_host("test")
    made_dir = False
    if not os.path.exists(test.path):
        os.mkdir(test.path)
        made_dir = True
    try:
        # backup
        res = cli.main(["backup", "config", "--to=test"])
        assert res == "Backed up targets 'orderly_volume', 'another_volume' to host 'test'"
        assert os.path.isfile(os.path.join(test.path, "orderly_volume.tar"))
        assert os.path.isfile(os.path.join(test.path, "another_volume.tar"))
        # restore
        res = cli.main(["restore", "config", "--from=test"])
        assert res == "Restored targets 'orderly_volume', 'another_volume' from host 'test'"
    finally:
        if made_dir:
            shutil.rmtree(test.path)


def test_restore_no_backups():
    res = cli.main(["restore", "config", "--from=test"])
    assert res == "No valid backups found. Doing nothing."
