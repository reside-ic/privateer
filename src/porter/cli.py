"""Usage:
  porter --version
  porter backup <path>
  porter restore <path>
"""

import docopt

import porter.__about__ as about


def main(argv=None):
    opts = docopt.docopt(__doc__, argv)
    if opts["--version"]:
        print(about.__version__)
        return about.__version__
    elif opts["backup"]:
        print("backing up targets")
        return "backup", opts["<path>"]
    elif opts["restore"]:
        print("restoring targets")
        return "restore", opts["<path>"]
