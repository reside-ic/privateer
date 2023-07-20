from unittest import mock

import pytest

from src.privateer import cli
from src.privateer.config import PrivateerTarget


def test_parse_args():
    with mock.patch("src.privateer.cli.restore") as r:
        r.return_value = ["orderly_volume", "another_volume"]
        res = cli.main(["restore", "config", "--from=uat"])
        assert res == "Restored targets 'orderly_volume', 'another_volume' from host 'uat'"

    with mock.patch("src.privateer.cli.restore") as r:
        r.return_value = ["orderly_volume"]
        res = cli.main(["restore", "config", "--from=uat"])
        assert res == "Restored target 'orderly_volume' from host 'uat'"

    with mock.patch("src.privateer.cli.get_targets") as t:
        res = cli.main(["backup", "config", "--to=uat", "--include=I", "--exclude=E"])
    assert t.call_count == 1
    assert t.call_args[0][0] == "I"
    assert t.call_args[0][1] == "E"
    assert len(t.call_args[0][2]) == 2
    assert t.call_args[0][2][0].name == "orderly_volume"
    assert res == "No targets selected. Doing nothing."

    res = cli.main(["restore", "config", "--from=uat", "--exclude=orderly_volume,another_volume"])
    assert res == "No targets selected. Doing nothing."

    msg = "Backed up targets 'orderly_volume', 'another_volume' to host 'test'"
    with mock.patch("src.privateer.cli.backup") as b:
        res = cli.main(["backup", "config", "--to=test"])
        assert res == msg
        assert b.called

    msg = "Backed up target 'orderly_volume' to host 'test'"
    with mock.patch("src.privateer.cli.backup") as b:
        res = cli.main(["backup", "config", "--to=test", "--include=orderly_volume"])
        assert res == msg
        assert b.called

    res = cli.main(["--version"])
    assert res == "0.0.3"


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
    e = "At most one of --include or --exclude should be provided."
    assert str(err.value) == e
