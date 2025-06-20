# Configuration

The system is configured via a single `json` document, `privateer.json` which contains information about all the moving parts: servers, clients, volumes and the vault configuration.

We imagine that your configuration will exist in some repo, and that that repo will be checked out on all involved machines. Please add `.privateer_identity` to your `.gitignore` for this repo.

A simple, complete, configuration could be:

```json
{
    "servers": [
        {
            "name": "alice",
            "hostname": "alice.example.com",
            "port": 10022,
            "key_volume": "privateer_keys",
            "data_volume": "privateer_data",
            "container": "privateer_server"
        }
    ],
    "clients": [
        {
            "name": "bob",
            "backup": ["data"]
        }
    ],
    "volumes": [
        {
            "name": "data"
        }
    ],
    "vault": {
        "url": "http://localhost:8200",
        "prefix": "/secret/privateer"
    }
}
```

The sections here are all required:

* `servers` contains an array of server locations.  Typically, you would have at least one as there's not a great deal of useful things that can be done with none.  Each server will correspond to a single machine (here, `alice.example.com`) and have a friendly name (here, `alice`).
* `clients` contains an array of clients that might push to or pull from the servers.  You will always have at least one client entry or you really cannot do anything useful.  Each client has a friendly name (here, `bob`) and a list of targets to back up.
* `volumes`: contains an array of volumes that we will back up and restore over the system.
* `vault`: contains information about connecting to the [HashiCorp Vault](https://www.vaultproject.io/) which contains the secrets that we will generate and use to connect from one machine to another.

There are some constraints that are enforced across sections of the configuration:

* The `name` fields must be unique across all clients and servers; no name can appear twice and no client can be a server.
* Every volume referenced by clients must appear in the `volumes` field, though you can have volumes listed in `volumes` that no client references.

We require the servers to explicitly set `key_volume` but not clients, because we expect that a single server machine might run multiple unrelated privateer servers, and that these will use different keys.  If you do this, each server also requires a different port.

## Practical considerations

We assume that `privateer.json` is committed to git, and that this is the mechanism for distributing and synchronising the configuration between machines.

## Details

::: privateer.config
