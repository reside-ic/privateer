# privateer

[![PyPI - Version](https://img.shields.io/pypi/v/privateer.svg)](https://pypi.org/project/privateer)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/privateer.svg)](https://pypi.org/project/privateer)

-----

**Table of Contents**

- [Usage](#usage)
- [Test](#test-and-lint)
- [Installation](#installation)
- [License](#license)

## Usage

```Usage:
  privateer --version
  privateer backup <path> --to=HOST [--exclude=TARGETS] [--include=INCLUDE]
  privateer restore <path> --from=HOST [--exclude=TARGETS] [--include=INCLUDE]

Options:
  --exclude=TARGETS  Comma separated string of target names to exclude (default is to include all)
  --include=TARGETS  Comma separated string of target names to include (default is to include all)
```

`<path>` is the path to a directory containing a `privateer.json` file. This file should contain at least one target 
and at least one host. See `./config/privateer.json` for an example. By default all targets in the config file are used, 
but this can be overridden by explicitly including or excluding targets by name.

## Test and lint

1. `hatch run test`
2. `hatch run lint:fmt`

To get coverage reported locally in the console, use `hatch run cov`. 
On CI, use `hatch run cov-ci` to generate an xml report.

## Installation

```console
pip install privateer
```

## License

`privateer` is distributed under the terms of the [MIT](https://spdx.org/licenses/MIT.html) license.
