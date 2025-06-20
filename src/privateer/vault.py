import os
import re

import hvac


def vault_client(addr: str, token: str | None = None) -> hvac.Client:
    """Create a vault client.

    This is a wrapper around vault methods in `hvac`, to simplify
    creation of a client.  It is mostly trying to smooth over fetching
    tokens.

    Args:

        addr: The vault address (url)

        token: An optional token.  This can be the actual token, the
            name of an environment variable in which the token is
            stored (starting with `$` and in all-caps), or `None`, in
            which case we check that `VAULT_TOKEN` and
            `VAULT_AUTH_GITHUB_TOKEN` variables (in that order) and
            fall back on interactively prompting for a token.

    """
    token = _get_vault_token(token)
    if _is_github_token(token):
        print("logging into vault using github")
        client = hvac.Client(addr)
        client.auth.github.login(token)
    else:
        client = hvac.Client(addr, token=token)
    return client


def _get_vault_token(token: str | None) -> str:
    if token is not None:
        re_envvar = re.compile("^\\$[A-Z0-9_-]+$")
        if re_envvar.match(token):
            token = os.environ[token[1:]]
        return token
    check = ["VAULT_TOKEN", "VAULT_AUTH_GITHUB_TOKEN"]
    for token_type in check:
        if token_type in os.environ:
            return os.environ[token_type]
    prompt = "Enter GitHub or Vault token to log into the vault:\n> "
    return input(prompt).strip()


def _is_github_token(token: str) -> bool:
    re_gh = re.compile("^ghp_[A-Za-z0-9]{36}$")
    return bool(re_gh.match(token))
