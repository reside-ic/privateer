import docker

from privateer.util import (
    container_exists,
    container_if_exists,
    ensure_image,
    mounts_str,
    ports_str,
)


# TODO: alias these types for mounts and ports somewhere
def service_command(
    image: str,
    name: str,
    *,
    mounts: list[docker.types.Mount] | None = None,
    ports: dict[str, int] | None = None,
    command: list[str] | None = None,
) -> list[str]:
    return [
        "docker",
        "run",
        "--rm",
        "-d",
        "--name",
        name,
        *mounts_str(mounts),
        *ports_str(ports),
        image,
        *(command or []),
    ]


def service_start(
    name: str,
    container_name: str,
    image: str,
    *,
    dry_run: bool = False,
    mounts: list[docker.types.Mount] | None = None,
    ports: dict[str, int] | None = None,
    command: list[str] | None = None,
) -> None:
    if dry_run:
        cmd = service_command(
            image, container_name, mounts=mounts, ports=ports, command=command
        )
        print("Command to manually launch service container:")
        print()
        print(f"  {' '.join(cmd)}")
        print()
        print("(remove the '-d' flag to run in blocking mode)")
        return

    if container_exists(container_name):
        msg = f"Container '{container_name}' for '{name}' already running"
        raise Exception(msg)

    ensure_image(image)
    print(f"Starting server '{name}' as container '{container_name}'")
    client = docker.from_env()
    client.containers.run(
        image,
        auto_remove=True,
        detach=True,
        name=container_name,
        mounts=mounts,
        ports=ports,
        command=command,
    )


def service_stop(name: str, container_name: str) -> None:
    container = container_if_exists(container_name)
    if container:
        if container.status == "running":
            container.stop()
    else:
        print(f"Container '{container_name}' for '{name}' does not exist")


def service_status(container_name: str) -> None:
    container = container_if_exists(container_name)
    if container:
        print(container.status)
    else:
        print("not running")
