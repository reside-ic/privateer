from unittest.mock import MagicMock, call

import privateer.vault
from privateer.util import transient_envvar
from privateer.vault import _get_vault_token, vault_client


def test_pass_back_given_token():
    assert _get_vault_token("a") == "a"


def test_lookup_token_from_env_if_given():
    with transient_envvar(MY_TOKEN="token"):
        assert _get_vault_token("$MY_TOKEN") == "token"


def test_fallback_on_known_good_tokens():
    with transient_envvar(VAULT_TOKEN="vt", VAULT_AUTH_GITHUB_TOKEN="gt"):
        assert _get_vault_token(None) == "vt"
    with transient_envvar(VAULT_TOKEN=None, VAULT_AUTH_GITHUB_TOKEN="gt"):
        assert _get_vault_token(None) == "gt"


def test_prompt_if_no_tokens_found(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda _: "foo")
    with transient_envvar(VAULT_TOKEN=None, VAULT_AUTH_GITHUB_TOKEN=None):
        assert _get_vault_token(None) == "foo"


def test_can_use_github_auth(monkeypatch):
    token = f"ghp_{'x' * 36}"
    mock_client = MagicMock()
    monkeypatch.setattr(privateer.vault.hvac, "Client", mock_client)
    client = vault_client("https://vault.example.com:8200", token)
    assert mock_client.call_count == 1
    assert mock_client.call_args == call("https://vault.example.com:8200")
    assert client == mock_client.return_value
    assert client.auth.github.login.call_count == 1
    assert client.auth.github.login.call_args == call(token)
