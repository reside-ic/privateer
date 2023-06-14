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

## Install from local sources

1. `hatch build`
2. `pip install dist/privateer-{version}.tar.gz`

## Publish to PyPi

Ensure you have built a new version of the package:
1. `hatch clean`
2. `hatch build`

Then publish to the test server:

```console
hatch publish -r test
```

You will be prompted to enter your [test.pypi.org](https://test.pypi.org/legacy/) username and password.
To test the installation, first run Python in a container:

```
docker run --rm -it --entrypoint bash python
```

Then:

```
pip install --index-url https://test.pypi.org/simple privateer --extra-index-url https://pypi.org/simple
```

Now you should be able to run `privateer` from the command line and see the usage instructions.

If it is working, you can publish to the real PyPi:

```console
hatch publish
```

## License

`privateer` is distributed under the terms of the [MIT](https://spdx.org/licenses/MIT.html) license.
