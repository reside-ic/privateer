# Development notes

Because this uses docker, vault and requires work with hostnames, this is going to be hard to test properly without a lot of mocking.  We'll update this as our strategy improves.

## Vault server for testing

We use [`vault-dev`](https://github.com/vimc/vault-dev) to bring up vault in testing mode.  You can also do this manually (e.g., to match the configuration in [`example/simple.json`](example/simple.json) by running

```
vault server -dev -dev-kv-v1
```

Then export the vault details by running:

```
export VAULT_ADDR='http://127.0.0.1:8200'
export VAULT_TOKEN=$(cat ~/.vault-token)
```

within the hatch environment before running any commands.

## Worked example

We need to swap in the globally-findable address for alice (`alice.example.com`) for the value of the machine this is tested on:

```
mkdir -p tmp
sed "s/alice.example.com/$(hostname)/" example/local.json > tmp/privateer.json
```

The following commands are all run from within `tmp/`

Create a set of keys

```
 keygen --all
```

You could also do this individually like

```
 keygen alice
```

Set up the key volumes

```
 configure alice
 configure bob
```

Start the server, as a background process (note that if these were on different machines the ` configure <name>` step would generate the `.privateer_identity` automatically so the `--as` argument is not needed)

```
 server --as=alice start
```

Once `alice` is running, we can test this connection from `bob`:

```
 check --as=bob --connection
```

Create some random data within the `data` volume (this is the one that we want to send from `bob` to `alice`)

```
docker volume create data
docker run -it --rm -v data:/data ubuntu bash -c "base64 /dev/urandom | head -c 100000 > /data/file1.txt"
```

We can now backup from `bob` to `alice` as:

```
 backup --as=bob data
```

or see what commands you would need in order to try this yourself:

```
 backup --as=bob --dry-run data
```

Delete the volume

```
docker volume rm data
```

We can now restore it:

```
 restore --as=bob data
```

or see the commands to do this ourselves:

```
 restore --as=bob data --dry-run
```

Tear down the server with

```
 server --as=alice stop
```

## Writing tests

We use a lot of global resources, so it's easy to leave behind volumes and containers (often exited) after running tests. At best this is lazy and messy, but at worst it creates hard-to-diagnose dependencies between tests. Try and create names for auto-cleaned volumes and containers using the `managed_docker` fixture (see [`tests/conftest.py`](tests/conftest.py) for details).
