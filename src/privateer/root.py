from pathlib import Path

from pydantic import BaseModel

from privateer.config import Config, read_config
from privateer.util import match_value


class Root(BaseModel):
    """A privateer root.

    Attributes:
        config: The privateer configuration

        path: The path to the privateer root directory

    """

    config: Config
    path: Path


def privateer_root(path: Path | None) -> Root:
    """Open a privateer root.

    Args:

        path: Optional path to the root.  If not given then we look
            for `privateer.json` in the current directory.

    Return:
        A `Root` object
    """
    if path is None:
        path = Path("privateer.json")
    elif path.is_dir():
        path = path / "privateer.json"
    if not path.exists():
        msg = f"Did not find privateer configuration at '{path}'"
        raise Exception(msg)
    return Root(config=read_config(path), path=path.parent)


# this could be put elsewhere; we find the plausible sources (original
# clients) that backed up a source to any server.
def find_source(cfg: Config, volume: str, source: str | None) -> str | None:
    if volume not in cfg.list_volumes():
        msg = f"Unknown volume '{volume}'"
        raise Exception(msg)
    for v in cfg.volumes:
        if v.name == volume and v.local:
            if source is not None:
                msg = f"'{volume}' is a local source, so 'source' must be empty"
                raise Exception(msg)
            return None
    pos = [cl.name for cl in cfg.clients if volume in cl.backup]
    return match_value(source, pos, "source")
