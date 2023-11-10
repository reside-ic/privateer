import docker
from privateer.check import check
from privateer.service import service_start, service_status, service_stop
from privateer.util import unique


def schedule_start(cfg, name, *, dry_run=False):
    machine = check(cfg, name, quiet=True)
    if not machine.schedule:
        msg = f"A schedule is not defined in the configuration for '{name}'"
        raise Exception(msg)

    mounts = [
        docker.types.Mount(
            "/privateer/keys", machine.key_volume, type="volume", read_only=True
        ),
    ]
    for v in unique([job.volume for job in machine.schedule.jobs]):
        mounts.append(
            docker.types.Mount(
                f"/privateer/volumes/{v}", v, type="volume", read_only=True
            )
        )
    port = machine.schedule.port
    service_start(
        name,
        machine.schedule.container,
        image=f"mrcide/privateer-client:{cfg.tag}",
        mounts=mounts,
        ports={f"{port}/tcp": port} if port else None,
        command=["yacron", "-c", "/privateer/keys/yacron.yml"],
        dry_run=dry_run,
    )


def schedule_stop(cfg, name):
    machine = check(cfg, name, quiet=True)
    service_stop(name, machine.schedule.container)


def schedule_status(cfg, name):
    machine = check(cfg, name, quiet=False)
    service_status(machine.schedule.container)
