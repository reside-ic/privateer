from unittest import mock

import pytest

from src.porter import cli
from src.porter.config import PorterTarget


def test_parse_args():
    with mock.patch("src.porter.cli.get_targets") as t:
        cli.main(["backup", "config", "--to=uat", "--include=I", "--exclude=E"])
    assert t.call_count == 1
    assert t.call_args[0][0] == "I"
    assert t.call_args[0][1] == "E"
    assert len(t.call_args[0][2]) == 2
    assert t.call_args[0][2][0].name == "orderly_volume"

    res = cli.main(["restore", "config", "--from=uat", "--exclude=orderly_volume,another_volume"])
    assert res == "No targets selected. Doing nothing."

    with mock.patch("src.porter.cli.backup") as b:
        res = cli.main(["backup", "config", "--to=test"])
        assert res == "Backed up targets 'orderly_volume', 'another_volume' to host 'test'"

    assert b.called

    res = cli.main(["restore", "config", "--from=uat"])
    assert res == "Restored targets 'orderly_volume', 'another_volume' from host 'uat'"

    res = cli.main(["--version"])
    assert res == "0.0.1"


def test_get_targets():
    all_targets = [PorterTarget({"name": "vol_1", "type": "volume"}), PorterTarget({"name": "vol_2", "type": "volume"})]
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
