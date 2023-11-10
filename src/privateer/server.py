import docker
from privateer.check import check
from privateer.service import service_start, service_status, service_stop


def server_start(cfg, name, *, dry_run=False):
    machine = check(cfg, name, quiet=True)

    mounts = [
        docker.types.Mount(
            "/privateer/keys", machine.key_volume, type="volume", read_only=True
        ),
        docker.types.Mount(
            "/privateer/volumes", machine.data_volume, type="volume"
        ),
    ]
    for v in cfg.volumes:
        if v.local:
            mounts.append(
                docker.types.Mount(
                    f"/privateer/local/{v.name}",
                    v.name,
                    type="volume",
                    read_only=True,
                )
            )
    service_start(
        name,
        machine.container,
        image=f"mrcide/privateer-server:{cfg.tag}",
        mounts=mounts,
        ports={"22/tcp": machine.port},
        dry_run=dry_run,
    )
    print(f"Server {name} now running on port {machine.port}")


def server_stop(cfg, name):
    machine = check(cfg, name, quiet=True)
    service_stop(name, machine.container)


def server_status(cfg, name):
    machine = check(cfg, name, quiet=False)
    service_status(machine.container)
