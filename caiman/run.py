"""
Caiman build system for MicroPython

Entry point for the caiman build system. This script is responsible for parsing the command line arguments and
loading the plugins that match the command. It then runs the plugins in order to build the MicroPython firmware.

(c) 2024 Andrei Dumitrache
"""
import argparse
import dataclasses
import json
import logging
import os
from pathlib import Path
from typing import Tuple

from caiman.config import DEFAULT_CONF_FILE, Command, Config
from caiman.proc.base import CommandError
from caiman.loader import get_pre_init_plugins, load_plugins
from caiman.plugins.base import Goal, Plugin, fail

_logger = logging.getLogger("caiman")


def get_arg_parser(goals: Tuple[Plugin]):
    parser = argparse.ArgumentParser(description="caiman - MicroPython build tool")
    goal_parsers = parser.add_subparsers(
        dest="goal",
        help="The goal to execute",
        required=True,
        title="Goals",
    )

    parser.add_argument(
        "--silent", help="Enable verbose output", action="store_true", default=False
    )
    parser.add_argument(
        "--force",
        help="Force the execution of the command",
        action="store_true",
        default=False,
    )

    for goal in goals:
        goal_parser = goal_parsers.add_parser(name=goal.name, help=goal.help)
        schema = goal.get_schema()
        for field in dataclasses.fields(schema):
            kwargs = {}
            if field.default is not dataclasses.MISSING:
                kwargs["default"] = field.default
                if type(field.default) is bool:
                    kwargs["action"] = "store_true"
            elif field.default_factory is not dataclasses.MISSING:
                kwargs["default_factory"] = field.default_factory
            else:
                kwargs["required"] = True
            goal_parser.add_argument(
                f"--{field.name}",
                help=field.metadata.get("help"),
                dest=f"params.{field.name}",
                **kwargs,
            )

    return parser


def get_goals(plugins: Tuple[Plugin]) -> Tuple[Goal]:
    plugin_by_goal = {}
    goals = []
    for plugin in plugins:
        for goal in plugin.get_goals():
            if goal.name in plugin_by_goal:
                fail(
                    f"Goal {goal.name} provided by multiple plugins: {plugin_by_goal[goal.name].name}, {plugin.name}"
                )
            plugin_by_goal[goal.name] = plugin
            goals.append(goal)

    return tuple(goals)


def main():
    plugins = []
    config_file = os.getenv("CAIMAN_CONFIG", DEFAULT_CONF_FILE)
    if not Path(config_file).exists():
        config = Config.default()
        plugins.extend(get_pre_init_plugins(config))
    else:
        config = Config.load(config_file)
        plugins.extend(load_plugins(config))

    goals = get_goals(plugins)

    parser = get_arg_parser(goals)
    args = parser.parse_args()
    logging.basicConfig(
        level=logging.ERROR if args.silent else logging.INFO,
        format="%(levelname)s [%(name)s] %(message)s",
    )

    if not args.silent:
        print(
            """

▗▄▄▖ ▗▄▖ ▗▄▄▄▖▗▖  ▗▖ ▗▄▖ ▗▖  ▗▖
▐▌   ▐▌ ▐▌  █  ▐▛▚▞▜▌▐▌ ▐▌▐▛▚▖▐▌
▐▌   ▐▛▀▜▌  █  ▐▌  ▐▌▐▛▀▜▌▐▌ ▝▜▌
▝▚▄▄▖▐▌ ▐▌▗▄█▄▖▐▌  ▐▌▐▌ ▐▌▐▌  ▐▌
================================
MicroPython build system
        """
        )

    _logger.info(f"Plugins: {', '.join([plugin.name for plugin in plugins])}")
    goal = next((g for g in goals if g.name == args.goal), None)
    if not goal:
        fail(f"Goal {args.goal} not provided by any plugin")

    goal_kwargs = {
        k.split(".", 1)[1]: v for k, v in vars(args).items() if k.startswith("params.")
    }
    command = Command(goal=goal.name, params=goal_kwargs, force=args.force)
    _logger.info(f"[{goal.name}] Running command: {command}")
    try:
        output = goal(command)
        if isinstance(output, bytes):
            print(output.decode("utf-8"))
        elif output:
            print(json.dumps(output, indent=2))
    except CommandError as e:
        fail(f"Board command error: {e}")

    if not DEFAULT_CONF_FILE.exists():
        fail(f"Config file {DEFAULT_CONF_FILE} does not exist")


if __name__ == "__main__":
    main()
