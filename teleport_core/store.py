import sys
from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, Field, RootModel
from rich import print
from xonsh.built_ins import XSH

from teleport_core.script_exit import ScriptExit


class Destination(BaseModel):
    name: str
    directory: Path
    date: datetime = Field(default_factory=lambda: datetime.now().astimezone())


Destinations = RootModel[list[Destination]]

_env = XSH.env
_destinations: dict[str, Destination] | None = None


def _config_location() -> Path:
    if _env is None:
        print("[yellow]looks like we are in a non-xonsh environment")
        return Path("./config.json")

    if "XONSH_TELEPORT_CONFIG_LOCATION" in _env:
        try:
            return Path(_env["XONSH_TELEPORT_CONFIG_LOCATION"]).expanduser()
        except Exception:
            print(
                "[red]💢 [bold]$XONSH_TELEPORT_CONFIG_LOCATION[/bold] is invalid!",
                file=sys.stderr,
            )
            raise ScriptExit()
    else:
        print(
            "[red]💢 You need to set [bold]$XONSH_TELEPORT_CONFIG_LOCATION[/bold] !",
            file=sys.stderr,
        )
        raise ScriptExit()


def load(force: bool = False):
    global _destinations

    if force or _destinations is None:
        config_location = _config_location()
        config_location.parent.mkdir(parents=True, exist_ok=True)

        if not config_location.exists():
            _destinations = {}
            return

        model = Destinations.model_validate_json(config_location.read_text())
        _destinations = {dest.name: dest for dest in model.root}


def _check_loaded() -> None:
    if _destinations is None:
        raise Exception("Config not loaded")


def save() -> None:
    _check_loaded()

    config_location = _config_location()
    config_location.parent.mkdir(parents=True, exist_ok=True)
    model = Destinations(_destinations.values())
    config_location.write_text(model.model_dump_json(indent=4))


def exists(name: str) -> bool:
    _check_loaded()

    return name in _destinations


def add(destination: Destination) -> None:
    _check_loaded()

    _destinations[destination.name] = destination


def remove(name: str) -> None:
    del _destinations[name]


def prune() -> list[Destination]:
    global _destinations
    new_dict = {}
    removed = []

    for dest in _destinations.values():
        if dest.directory.exists():
            new_dict[dest.name] = dest
        else:
            removed.append(dest)

    _destinations = new_dict

    return removed


def clear() -> None:
    _destinations.clear()


def all() -> list[Destination]:
    return list(_destinations.values())


def get(name: str) -> Path:
    return _destinations[name].directory
