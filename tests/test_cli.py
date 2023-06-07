from src.porter import cli


def test_parse_args():
    res = cli.main(["backup", "config"])
    assert res == ("backup", "config")

    res = cli.main(["restore", "config"])
    assert res == ("restore", "config")

    res = cli.main(["--version"])
    assert res == "0.0.1"
