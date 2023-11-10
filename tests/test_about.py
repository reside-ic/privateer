import re

from privateer.__about__ import __version__ as privateer_version


def test_version_has_required_format():
    re.match("^[0-9]+\\.[0-9]+\\.[0-9]+$", privateer_version)
