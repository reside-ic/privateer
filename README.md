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
  privateer backup <path> --to=HOST [--exclude=TARGETS] [--include=TARGETS]
  privateer restore <path> --from=HOST [--exclude=TARGETS] [--include=TARGETS] [--y]
  privateer schedule <path> --to=HOST [--exclude=TARGETS] [--include=TARGETS]
  privateer status
  privateer cancel [--host=HOST]

Options:
  --exclude=TARGETS  Comma separated string of target names to exclude (default is to include all)
  --include=TARGETS  Comma separated string of target names to include (default is to include all)
  --host=HOST  Backup host to cancel scheduled backups for (default is to cancel all)
  --y  Restore without further prompting
```

`<path>` is the path to a directory containing a `privateer.json` file. This file should contain at least one target 
and at least one host. See `./config/privateer.json` for an example. By default all targets in the config file are used, 
but this can be overridden by explicitly including or excluding targets by name. 

### Manual backups
Backups can be run manually with `privateer backup`. In this case the backup filename with be of the format:

```<volume_name>-<machine_name>-%Y-%m-%dT%H-%M-%S.tar.gz``` 

where `machine_name` is the name of the soure machine.

### Scheduling
Backups can be scheduled by specifying cron schedules in `privateer.json` and running `privateer schedule`. 
In this case backup filenames will be of the format 

```<volume_name>-<schedule_name>-<machine_name>-%Y-%m-%dT%H-%M-%S.tar.gz```

Backups can be scheduled to multiple hosts simultaneously by running `privateer schedule` multiple times.

### Cancelling backups
Cancel scheduled backups with `privateer cancel`. By default this stops all scheduled backups, but if 
multiple hosts are being backed up to, backups to a single host can be cancelled using the `--host` option.

### Restoring
Restoring is always a manual process, run with `privateer restore`. By default it will prompt before restoring each
target, so that the user can inspect the filename that is being restored (to e.g. check that the backup being restored 
has the expected machine name). To bypass prompting, pass the `--y` option.

Note that the latest backup will always be restored (restoring from a specific date will be supported in a future release).

### Status
`privateer status` returns the status of all backups currently scheduled, in json format. E.g.

```bash
$ privateer status
2 hosts receiving backups:
{
    "host": {
        "name": "another_test",
        "host_type": "local",
        "path": "/home/aehill/Documents/dev/reside/privateer/another_starport"
    },
    "targets": [
        {
            "name": "another_volume",
            "type": "volume",
            "schedules": [
                {
                    "name": "custom",
                    "schedule": "* * * * *",
                    "retention_days": 12
                }
            ]
        }
    ]
}
{
    "host": {
        "name": "test",
        "host_type": "local",
        "path": "/home/aehill/Documents/dev/reside/privateer/starport"
    },
    "targets": [
        {
            "name": "orderly_volume",
            "type": "volume",
            "schedules": [
                {
                    "name": "daily",
                    "schedule": "0 2 * * *",
                    "retention_days": 7
                }
            ]
        }
    ]
}

```


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
