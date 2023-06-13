# porter

[![PyPI - Version](https://img.shields.io/pypi/v/porter.svg)](https://pypi.org/project/porter)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/porter.svg)](https://pypi.org/project/porter)

-----

**Table of Contents**

- [Usage](#usage)
- [Test](#test-and-lint)
- [Installation](#installation)
- [License](#license)

## Usage

```Usage:
  porter --version
  porter backup <path> --to=HOST [--exclude=TARGETS] [--include=INCLUDE]
  porter restore <path> --from=HOST [--exclude=TARGETS] [--include=INCLUDE]

Options:
  --exclude=TARGETS  Comma separated string of target names to exclude (default is to include all)
  --include=TARGETS  Comma separated string of target names to include (default is to include all)
```

`<path>` is the path to a directory containing a `porter.json` file. This file should contain at least one target 
and at least one host. See `./config/porter.json` for an example. By default all targets in the config file are used, 
but this can be overridden by explicitly including or excluding targets by name.

## Test and lint

1. `hatch run test`
2. `hatch run lint:fmt`

To get coverage reported locally in the console, use `hatch run cov`. 
On CI, use `hatch run cov-ci` to generate an xml report.

## Installation

```console
pip install porter
```

## License

`porter` is distributed under the terms of the [MIT](https://spdx.org/licenses/MIT.html) license.
