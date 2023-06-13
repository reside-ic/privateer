from unittest import mock

import pytest

from src.privateer import cli
from src.privateer.config import PrivateerTarget


def test_parse_args():
    res = cli.main(["backup", "config", "--to=uat"])
    assert res == "Backing up targets 'orderly_volume', 'another_volume' to host 'uat'"

    res = cli.main(["restore", "config", "--from=uat"])
    assert res == "Restoring targets 'orderly_volume', 'another_volume' from host 'uat'"

    res = cli.main(["restore", "config", "--from=uat", "--exclude=orderly_volume, another_volume"])
    assert res == "No targets selected. Doing nothing."

    with mock.patch("src.privateer.cli.get_targets") as t:
        cli.main(["backup", "config", "--to=uat", "--include=I", "--exclude=E"])
    assert t.call_count == 1
    assert t.call_args[0][0] == "I"
    assert t.call_args[0][1] == "E"
    assert len(t.call_args[0][2]) == 2
    assert t.call_args[0][2][0].name == "orderly_volume"

    res = cli.main(["--version"])
    assert res == "0.0.1"


def test_get_targets():
    all_targets = [
        PrivateerTarget({"name": "vol_1", "type": "volume"}),
        PrivateerTarget({"name": "vol_2", "type": "volume"}),
    ]
    res = cli.get_targets("vol_1,vol_2", None, all_targets)
    assert len(res) == 2
    assert res == all_targets

    res = cli.get_targets("vol_1, vol_2", None, all_targets)
    assert len(res) == 2
    assert res == all_targets

    res = cli.get_targets(None, "vol_1, vol_2", all_targets)
    assert len(res) == 0

    res = cli.get_targets("vol_1", None, all_targets)
    assert len(res) == 1
    assert res[0].name == "vol_1"

    res = cli.get_targets(None, "vol_2", all_targets)
    assert len(res) == 1
    assert res[0].name == "vol_1"

    with pytest.raises(Exception) as err:
        cli.get_targets("vol_1", "vol_2", all_targets)
    assert str(err.value) == "At most one of --include or --exclude should be provided."
