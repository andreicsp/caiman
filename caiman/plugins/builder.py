from dataclasses import dataclass
import logging
import subprocess
import sys
from typing import Tuple

from caiman.config import Command, Config
from caiman.plugins.base import Goal, Plugin, fail, param

from pathlib import Path

from caiman.target import WorkspaceSource

_logger = logging.getLogger(__name__)


@dataclass
class BuildCommand:
    target: str = param("The target to build", default="")

    @property
    def builder(self):
        return self.target.split(":")[0] if ":" in self.target else None

    @property
    def builder_target(self):
        return self.target.split(":")[1] if ":" in self.target else self.target


class Builder:
    def __init__(self, config: Config):
        self.config = config
        self._logger = logging.getLogger(self.__class__.__name__)

    @property
    def targets(self):
        yield from []

    def __call__(self, command: Command):
        targets = list(self.targets)
        self._logger.info(f"Building targets: {', '.join(target.source.name for target in targets)}")
        for target in targets:
            self._build_target(target)


class ResourceBuilder(Builder):
    @property
    def targets(self):
        yield from [WorkspaceSource(workspace=self.config.workspace, source=source) for source in self.config.resources]

    def _copy_file(self, source_file: Path, target_file: Path, source: WorkspaceSource):
        _logger.info(f"Copying {source_file} to {target_file}")
        target_file.parent.mkdir(parents=True, exist_ok=True)
        target_file.write_bytes(source_file.read_bytes())

    def _build_target(self, source: WorkspaceSource):
        self._logger.info(f"Building {source.source.name}")
        for source_file, target_file in source.copy_tuples():
            self._copy_file(source_file, target_file, source=source)

        manifest = source.create_target_manifest()
        source.save_manifest(manifest)


class SourceBuilder(ResourceBuilder):
    @property
    def targets(self):
        yield from [WorkspaceSource(workspace=self.config.workspace, source=source) for source in self.config.sources]

    def _compile_file(self, source_file: Path, target_file: Path):
        self._logger.info(f"Compiling {source_file} to {target_file}")
        target_file.parent.mkdir(parents=True, exist_ok=True)
        command = [sys.executable, "-m", "mpy_cross_v6", str(source_file), "-o", str(target_file)]
        try:
            subprocess.run(command, check=True, stderr=subprocess.PIPE)
        except subprocess.CalledProcessError as e:
            _logger.error(f"Command '{command}' returned non-zero exit status {e.returncode}.")
            fail(f"Error output: {e.stderr.decode('utf-8')}")

    def _copy_file(self, source_file: Path, target_file: Path, source: WorkspaceSource):
        if source_file.suffix == ".py" and source.source.compile:
            self._compile_file(source_file, target_file)
        else:
            super()._copy_file(source_file=source_file, target_file=target_file, source=source)


class BuildGoal(Goal):
    def __init__(self, config):
        self.config = config

    @property
    def help(self):
        return "Build dependencies, tools, sources, and resources"

    @property
    def name(self):
        return "build"

    def get_schema(self):
        return BuildCommand

    @property
    def builders(self):
        return {
            "resources": ResourceBuilder(self.config),
            "sources": SourceBuilder(self.config),
        }
 
    def __call__(self, command: Command):
        goal_command = BuildCommand(**command.params)
        for name, builder in self.builders.items():
            if not goal_command.builder_target or goal_command.builder == name:
                builder(command)


class ApplicationBuilderPlugin(Plugin):
    def get_goals(self) -> Tuple[Goal]:
        return (BuildGoal(self.config), )
