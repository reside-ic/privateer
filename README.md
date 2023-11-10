# privateer

[![PyPI - Version](https://img.shields.io/pypi/v/privateer.svg)](https://pypi.org/project/privateer)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/privateer.svg)](https://pypi.org/project/privateer)

-----

## The idea

We need a way of synchronising some docker volumes from a machine to some backup server, incrementally, using `rsync`. We previously used [`offen/docker-volume-backup`](https://github.com/offen/docker-volume-backup) to backup volumes in their entirety to another machine as a tar file but the space and time requirements made this hard to use in practice.

### The setup

We assume some number of **server** machines -- these will receive data, and some number of **client** machines -- these will send data to the server(s).  A client can back any number of volumes to any number of servers, and a server can receive and serve any number of volumes to any number of clients.

A typical framework for us would be that we would have a "production" machine which is backing up to one or more servers, and then some additional set of "staging" machines that receive data from the servers, which in practice never send any data.

Because we are going to use ssh for transport, we assume existence of [HashiCorp Vault](https://www.vaultproject.io/) to store secrets.

### Configuration

The system is configured via a single `json` document, `privateer.json` which contains information about all the moving parts: servers, clients, volumes and the vault configuration. See [`example/`](example/) for some examples.

We imagine that your configuration will exist in some repo, and that that repo will be checked out on all involved machines. Please add `.privateer_identity` to your `.gitignore` for this repo.

### Setup

After writing a configuration, on any machine run

```
privateer keygen --all
```

which will generate ssh keypairs for all machines and put them in the vault. This only needs to be done once, but you might need to run it again if

* you add more machines to your system
* you want to rotate keys

Once keys are written to the vault, on each machine run

```
privateer configure <name>
```

replacing `<name>` with the name of the machine within either the `servers` or `clients` section of your configuration.  This sets up a special docker volume that will persist ssh keys and configurations so that communication between clients and servers is straightforward and secure.  It also leaves a file `.privateer_identity` at the same location as the configuration file, which is used as the default identity for subsequent commands. Typically this is what you want.

Servers must be started before any backup is possible. To do this, run

```
privateer server start
```

Once started you can stop a server with `privateer server stop` (or just kill the container) and find out how it's getting on with `privateer server status`

### Manual backup

To back up a volume onto one of your configured servers, run:

```
privateer backup <volume> [--server=NAME]
```

Add `--dry-run` to see the commands to run it yourself.

### Scheduled backups

Each client can run a long-lived container to perform backups on some schedule using [`yacron`](https://github.com/gjcarneiro/yacron). If your client configuration contains a `schedule` section then you can run the command

```
privateer schedule start
```

to start the scheduled tasks.

### Restore

Restoration is always manual

```
privateer restore <volume> [--server=NAME] [--source=NAME]
```

where `--server` controls the server you are pulling from (useful if you have more than one configured) and `--source` controls the original machine that backed the data up (if more than one machine is pushing backups).

For example, if you are on a "staging" machine, connecting to the "backup" server and want to pull the "user_data" volume that was backed up from "production" machine called  you would type

```
privateer restore user_data --server=backup --source=production
```

### Point-in-time backup and recovery

Point-in-time backup is always taken on the server side, and converts a copy of a volume held on the server to a `tar` file, on the host machine and outside of any docker volume. These can then be manually copied around and use to initialise the contents of new volumes, in a way similar to the normal restore path.

The command to export the volume is:

```
privateer export <volume> [--to-dir=PATH] [--source=NAME]
```

which will bring up a new container and create the tar file within the directory `PATH`. The name will be automatically generated and include the curent time, volume name and source.  The `source` argument controls who backed the volume up in the first place, in the case where there are multiple clients.  It can be omitted in the case where there is only one client performing backups, and **must** be ommitted in the case where you are exporting a local volume.

You can point this command at any volume on any system where `privateer` is installed to make a `tar` file; this might be useful for ad-hoc backup and recovery. If you have a volume called `redis_data`, then

```
privateer export redis_data
```

will create a new file `redis_data-<timestamp>.tar` in your working directory.

Given a `tar` file, recovery looks like:

```
privateer [--dry-run] import <tarfile> <volume>
```

This does not need to be run anywhere with a `privateer.json` configuration, and indeed does not try and read one. It will fail if the volume exists already, making the command fairly safe.

We could copy the file created in the `redis_data` example above to another machine and run

```
privateer import redis_data-<timestamp>.tar redis_data
```

to export the `tar` file into a new volume `redis_data`.

## What's the problem anyway?

[Docker volumes](https://docs.docker.com/storage/volumes/) are useful for abstracting away some persistent storage for an application. They're much nicer to use than bind mounts because they don't pollute the host system with immovable files (docker containers often running as root or with a uid different to the user running docker).  The docker [docs](https://docs.docker.com/storage/volumes/#back-up-restore-or-migrate-data-volumes) describe some approaches to backup and restore but in practice this ignores many practical issues, especially when the volumes are large or off-site backup is important.

We want to be able to synchronise a volume to another volume on a different machine; our setup looks like this:

```
bob                            alice
+-------------------+          +-----------------------+
|                   |          |                       |
| application       |          |                       |
|  |                |          |                       |
| volume1           |          |     volume2           |
|  |                |   ssh/   |      |                |
| privateer-client--=----------=---> privateer-server  |
|  |                |  rsync   |      |                |
| keys              |          |     keys              |
|                   |          |                       |
+-------------------+          +-----------------------+
```

so in this case `bob` runs a `privateer` client which sends data over ssh+rsync to a server running on `alice`, eventually meaning that the data in `volume1` on `bob` is replicated to `volume2` on `alice`.  This process uses a set of ssh keys that each client and server will hold in a `keys` volume.  This means that they do not interact with any ssh systems on the host.  Note that if `alice` is also running sshd, this backup process will use a *second* ssh connection.

In addition, we will support point-in-time backups on `alice`, creating `tar` files of the volume onto disk that can be easily restored onto any host.

## Installation

```console
pip install privateer
```

## License

`privateer` is distributed under the terms of the [MIT](https://spdx.org/licenses/MIT.html) license.
