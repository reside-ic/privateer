# `privateer`

This is a package for backing up, restoring and otherwise working with [docker volumes](https://docs.docker.com/engine/storage/volumes/).  The package implements a simple scheme based on `rsync` and `ssh` to move content from a docker volume on one machine to a backup server on another, and from there perhaps to a third machine.  It also provides utilities for creating tarballs of these volumes and importing them into new volumes.

## Why is this needed?

The [official docker docs have a section on backing up and restoring volumes](https://docs.docker.com/engine/storage/volumes/#back-up-restore-or-migrate-data-volumes) but the general recommendation is to make a tarball of a volume and move that around yourself.  We previously used [`offen/docker-volume-backup`](https://github.com/offen/docker-volume-backup) to backup volumes in their entirety to another machine as a tar file but the space and time requirements made this hard to use in practice.

What we wanted is a system that would use `rsync` to move as little data as possible, and not require storing on one machine both the data in the volume **and** the tarball, which means that backups become impossible as disk space becomes low -- which in our experience was a situation where backups became critically important.

### The setup

We assume some number of **server** machines -- these will receive data, and some number of **client** machines -- these will send data to the server(s).  A client can back any number of volumes to any number of servers, and a server can receive and serve any number of volumes to any number of clients.

A typical framework for us would be that we would have a "production" machine which is backing up to one or more servers, and then some additional set of "staging" machines that receive data from the servers, which in practice never send any data (though they could if one wanted them to).

Because we are going to use ssh for transport, we assume existence of [HashiCorp Vault](https://www.vaultproject.io/) to store secrets.

### Configuration

The system is configured via a single `json` document, `privateer.json` which contains information about all the moving parts: servers, clients, volumes and the vault configuration.  See the [configuration documentation](config.md) for more details.

We imagine that your configuration will exist in some repo, and that that repo will be checked out on all involved machines. Please add `.privateer_identity` to your `.gitignore` for this repo.
