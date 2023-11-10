import pytest

from privateer.backup import backup_command
from privateer.config import read_config
from privateer.util import current_timezone_name
from privateer.yacron import _validate_yacron_yaml, generate_yacron_yaml


def test_can_generate_yacron_yaml():
    cfg = read_config("example/schedule.json")
    cfg.clients[0].schedule.port = None
    cfg.clients[0].schedule.jobs.pop()
    res = generate_yacron_yaml(cfg, "bob")
    expected = [
        "defaults:",
        f'  timezone: "{current_timezone_name()}"',
        "jobs:",
        '  - name: "job-1"',
        f"    command: \"{' '.join(backup_command('bob', 'data1', 'alice'))}\"",
        '    schedule: "@daily"',
    ]
    assert _validate_yacron_yaml(res)
    assert res == expected


def test_can_generate_empty_yacron_yaml_for_server():
    cfg = read_config("example/simple.json")
    assert generate_yacron_yaml(cfg, "alice") is None


def test_can_generate_empty_yacron_yaml_for_client_with_no_schedule():
    cfg = read_config("example/simple.json")
    assert generate_yacron_yaml(cfg, "bob") is None


def test_can_add_web_interface():
    cfg = read_config("example/schedule.json")
    cfg.clients[0].schedule.jobs.pop()
    res = generate_yacron_yaml(cfg, "bob")
    expected = [
        "defaults:",
        f'  timezone: "{current_timezone_name()}"',
        "web:",
        "  listen:",
        "    - http://0.0.0.0:8080",
        "jobs:",
        '  - name: "job-1"',
        f"    command: \"{' '.join(backup_command('bob', 'data1', 'alice'))}\"",
        '    schedule: "@daily"',
    ]
    assert _validate_yacron_yaml(res)
    assert res == expected


def test_can_check_yacron_config_is_valid():
    valid = [
        "jobs:",
        "- name: name",
        "  command: command",
        "  schedule: '@daily'",
    ]
    assert _validate_yacron_yaml(valid)

    # Missing a key
    with pytest.raises(Exception, match="command"):
        _validate_yacron_yaml(valid[:-1])

    # Syntax error:
    with pytest.raises(Exception, match="mapping"):
        _validate_yacron_yaml(valid[1:])
