from dataclasses import asdict, dataclass
import logging
import subprocess
import sys
from typing import Iterable, Tuple
from caiman.config import Command, Config, Dependency, Resource, Source, Tool
from caiman.plugins.base import Goal, Plugin, fail, param
from caiman.plugins.installer import MIPInstallerPlugin

from pathlib import Path
from abc import abstractmethod

_logger = logging.getLogger(__name__)


class Builder:

    def __init__(self, config: Config):
        self.config = config

    @abstractmethod
    def build(self, buildable):
        pass

    @abstractmethod
    def buildables(self):
        yield from []

    @property
    @abstractmethod
    def target(self):
        pass

    def run(self, command: Command):
        for builder, buildable in self.buildables():
            builder.build(buildable)


class DependencyBuilder(Builder):
    _installers_by_channel = {}

    def __init__(self, config):
        super().__init__(config=config)
        self._installer = MIPInstallerPlugin(config)

    @property
    def target(self):
        return "dependencies"

    def get_package_folder(self):
        return self.config.workspace.packages

    def build(self, dep: Dependency):
        self._installer.install(dep)

    def _get_buildable(self, dep: Dependency):
        return self, dep

    def buildables(self) -> Iterable:
        for dep in self.config.dependencies:
            builder, dep = self._get_buildable(dep)
            yield builder, dep

        source = Source(
            path=str(Path(self.config.root_path) / self.get_package_folder()),
            target=str(self.config.workspace.build),
            compile=True
        )

        yield SourceBuilder(config=self.config), source


class ToolBuilder(DependencyBuilder):
    def get_package_folder(self):
        return self.config.workspace.tools

    def buildables(self) -> Iterable:
        return map(self._get_buildable, self.config.tools)
    
    @property
    def target(self):
        return "tools"


class ResourceBuilder(Builder):

    def get_copy_paths(self, resource: Resource):
        for source_file in Path(resource.path).rglob(resource.pattern):
            if not any(source_file.match(pattern) for pattern in self.config.workspace.ignores):
                target_file = Path(resource.target) / source_file.relative_to(resource.path)
                yield source_file, target_file

    def _copy_file(self, source_file: Path, target_file: Path):
        target_file.parent.mkdir(parents=True, exist_ok=True)
        _logger.info(f"Copying {source_file} to {target_file}")
        target_file.write_bytes(source_file.read_bytes())

    def _get_buildable(self, resource: Resource):
        path = Path(self.config.root_path) / self.config.workspace.sources / resource.path
        target = Path(self.config.root_path) / self.config.workspace.build / resource.target.lstrip("/")
        kwargs = asdict(resource)
        kwargs.update(dict(path=str(path), target=str(target)))
        return self, resource.__class__(**kwargs)

    def buildables(self) -> Iterable:
        return map(self._get_buildable, self.config.resources)

    def build(self, resource: Resource):
        for source_file, target_file in self.get_copy_paths(resource):
            self._copy_file(source_file, target_file)

    @property
    def target(self):
        return "resources"


class SourceBuilder(ResourceBuilder):
    def _compile_file(self, source_file: Path, target_file: Path):
        source = str(source_file)
        target = str(target_file)

        _logger.info(f"Compiling {source} to {target}")
        command = [sys.executable, "-m", "mpy_cross_v6", source, "-o", target]
        try:
            subprocess.run(command, check=True, stderr=subprocess.PIPE)
        except subprocess.CalledProcessError as e:
            _logger.error(f"Command '{command}' returned non-zero exit status {e.returncode}.")
            fail(f"Error output: {e.stderr.decode('utf-8')}")

    def buildables(self) -> Iterable:
        return map(self._get_buildable, self.config.sources)

    def build(self, source: Source):
        for source_file, target_file in self.get_copy_paths(source):
            if source_file.suffix == ".py":
                target_file.parent.mkdir(parents=True, exist_ok=True)
                if source.compile:
                    target_file = target_file.with_suffix(".mpy")
                    self._compile_file(source_file, target_file)
                else:
                    self._copy_file(source_file, target_file)

    def match_command(self, command: Command):
        return command.goal == "build" and command.target == "sources"
    
    @property
    def target(self):
        return "sources"
    

@dataclass
class BuildCommand:
    target: str = param("The target to build {dependencies,tools,sources,resources}", default="")


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

    def __call__(self, command: Command):
        goal_command = BuildCommand(**command.params)
        for builder in [DependencyBuilder, ToolBuilder, SourceBuilder, ResourceBuilder]:
            builder_obj = builder(self.config)
            if not goal_command.target or builder_obj.target == goal_command.target:
                builder_obj.run(command)


class ApplicationBuilder(Builder, Plugin):
    def get_goals(self) -> Tuple[Goal]:
        return (
            BuildGoal(self.config),
        )
