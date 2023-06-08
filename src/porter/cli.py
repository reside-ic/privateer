"""Usage:
  porter --version
  porter backup <path> --to=HOST
  porter restore <path> --from=HOST
"""

import docopt

import porter.__about__ as about

from src.porter.config import PorterConfig


def main(argv=None):
    opts = docopt.docopt(__doc__, argv)
    if opts["--version"]:
        print(about.__version__)
        return about.__version__
    cfg = PorterConfig(opts["<path>"])
    if opts["backup"]:
        msg = f"Backing up targets to host '{cfg.get_host(opts['--to']).name}'"
        print(msg)
        return msg
    elif opts["restore"]:
        msg = f"Restoring targets from host '{cfg.get_host(opts['--from']).name}'"
        print(msg)
        return msg
