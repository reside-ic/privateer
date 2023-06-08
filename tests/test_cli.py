from src.porter import cli


def test_parse_args():
    res = cli.main(["backup", "config", "--to=annex"])
    assert res == "Backing up targets to host 'annex'"

    res = cli.main(["restore", "config", "--from=annex"])
    assert res == "Restoring targets from host 'annex'"

    res = cli.main(["--version"])
    assert res == "0.0.1"
