import os
import sys
from argparse import ArgumentParser
from pathlib import Path

from rich import print
from xonsh.built_ins import XSH, XonshSession

from teleport_core import store
from teleport_core.script_exit import ScriptExit
from teleport_core.store import Destination

__all__ = ()

parser = ArgumentParser(prog="teleport")
parser.add_argument(
    "name",
    nargs="?",
    default=None,
    type=str,
    help="destination to teleport to, or the name of the destination to add",
)
parser.add_argument(
    "-r",
    "--remove",
    action="store_true",
    default=False,
    help="remove a directory from teleport destinations",
)
parser.add_argument(
    "--prune",
    action="store_true",
    default=False,
    help="remove all destinations that are nonexistent",
)
parser.add_argument(
    "--clear",
    action="store_true",
    default=False,
    help="remove ALL destinations",
)
parser.add_argument(
    "--reload",
    action="store_true",
    default=False,
    help="reload config",
)
parser.add_argument(
    "-l",
    "--list",
    action="store_true",
    default=False,
    help="list destinations",
)
parser.add_argument("--clear-all", action="store_true", help="clear all destinations")
group = parser.add_argument_group("adding destinations")
group.add_argument(
    "-a",
    "--add",
    action="store_true",
    default=False,
    help="add a directory as a teleport destination",
)
group.add_argument(
    "-d",
    "--directory",
    default=None,
    type=str,
    help="manually specify the directory that should be added",
)
group.add_argument(
    "-o",
    "--overwrite",
    default=False,
    action="store_true",
    help="overwrite an existing destination if it exists",
)


class Args:
    name: str
    directory: str
    add: bool
    remove: bool
    prune: bool
    clear: bool
    overwrite: bool
    reload: bool
    list: bool


def _main_wrapper(_args: list[str] = None):
    try:
        _main(_args)
    except ScriptExit:
        pass


def _main(_args: list[str] = None):
    store.load()

    if _args:
        args: Args = parser.parse_args(_args)
    else:
        args: Args = parser.parse_args()

    _check_args(args)

    current_dir = Path().absolute()
    name = args.name or current_dir.name.lower()

    if args.add:
        if not args.overwrite and store.exists(args.name):
            print(
                "[red]💢 a destination with that name already exists! pass [bold]--overwrite[/bold] or [bold]-o[/bold] to ignore"
            )
        else:
            directory = args.directory or current_dir

            store.add(Destination(name=name, directory=directory))
            store.save()

            print(f"Added [bold]{name}[/bold] as {directory}")
    elif args.remove:
        if not store.exists(name):
            print("[red]💢 no destination with that name exists")
        else:
            store.remove(name)
            store.save()

            print(f"🗑️ Removed [bold]{name}'[bold]")
    elif args.prune:
        prune_list = store.prune()
        store.save()

        for pruned in prune_list:
            print(
                f"🗑️ Removed [bold]{pruned.name}[bold] ([red]{pruned.directory}[/red])"
            )
    elif args.clear:
        store.clear()
        store.save()

        print("🗑️ Cleared all destinations")
    elif args.reload:
        store.load(force=True)
    elif args.list:
        for dest in store.all():
            print(f"[bold]{dest.name}[/bold] {dest.directory}")
    else:
        if not store.exists(args.name):
            print("[red]💢 no destination with that name exists")
        else:
            dest = store.get(args.name)

            if not dest.exists():
                print(
                    "[red]⛔️ the directory for that destination does not exist. use [bold]--prune[/bold] to remove dangling destinations"
                )
                return

            os.chdir(dest)


def _check_args(args: Args) -> None:
    if not any(args.__dict__.values()):
        parser.print_help()
        raise ScriptExit()

    def check_used_alone(name: str) -> bool:
        nonlocal args

        if args.__dict__[name] and any(
            [v for k, v in args.__dict__.items() if k != name]
        ):
            print(f"[red]💢 --{name} must be used alone", file=sys.stderr)
            return True

        return False

    if args.add and args.remove:
        print("[red]💢 --add AND --remove??? what madness is this?", file=sys.stderr)
    elif args.directory and not args.add:
        print("[red]💢 --directory can only be used with --add", file=sys.stderr)
    elif args.overwrite and not args.add:
        print("[red]💢 --overwrite can only be used with --add", file=sys.stderr)
    elif not any(
        [check_used_alone(name) for name in ["clear", "reload", "prune", "list"]]
    ):
        return

    raise ScriptExit()


def _load_xontrib_(xsh: XonshSession, **kwargs) -> dict:
    XSH.aliases["tp"] = _main_wrapper
    XSH.aliases["teleport"] = _main_wrapper

    return {}


def _unload_xontrib_(xsh: XonshSession, **kwargs) -> dict:
    del XSH.aliases["tp"]
    del XSH.aliases["teleport"]

    return {}
