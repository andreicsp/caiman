import logging
import shutil
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Tuple

from caiman.config import Command, Config
from caiman.installer import DependencyInstaller, ToolInstaller
from caiman.plugins.base import Goal, Plugin, param
from caiman.source import WorkspacePythonSource, WorkspaceSource


@dataclass
class BuildCommand:
    target: str = param("Target to build", default="")
    force: bool = param("Force build", default=False)

    @property
    def builder(self):
        return self.target.split(":", 1)[0] if self.target else None

    @property
    def buildable(self):
        parts = self.target.split(":", 1)
        return self.target.split(":", 1)[1] if len(parts) > 1 else None


class Builder(ABC):
    def __init__(self, config: Config):
        self.config = config
        self._logger = logging.getLogger(f"build:{self.name}")

    @property
    def name(self):
        return self.__class__.__name__

    @property
    def buildables(self):
        yield from []

    def get_command_buildables(self, command: BuildCommand):
        if command.buildable:
            return [
                buildable
                for buildable in self.buildables
                if command.buildable == buildable.source.name
            ]
        return list(self.buildables)

    @abstractmethod
    def _build(self, source: WorkspaceSource, command: BuildCommand):
        """
        Process a buildable source.
        """

    def __call__(self, command: BuildCommand):
        buildables = self.get_command_buildables(command)
        if not buildables:
            if not command.builder:
                return
            raise RuntimeError(
                f"No buildable sources found for target '{command.target}'"
            )

        self._logger.info(
            f"Building targets: {', '.join(buildable.source.name for buildable in buildables)}"
        )
        for buildable in buildables:
            if not command.buildable or command.buildable == buildable.source.name:
                self._build(buildable, command=command)


class ResourceBuilder(Builder):
    @property
    def name(self):
        return "resources"

    @property
    def buildables(self):
        yield from [
            WorkspaceSource(workspace=self.config.workspace, source=source)
            for source in self.config.resources
        ]

    def _build(self, source: WorkspaceSource, command: BuildCommand):
        self._logger.info(f"Building {source.source.name}")
        source.manifests.save(source.create_manifest())
        deployment = source.create_deployment()
        manifest = deployment(logger=self._logger)
        self._logger.info(f"Saving {source.source.name} manifest")
        deployment.manifests.save(manifest)


class SourceBuilder(ResourceBuilder):
    @property
    def name(self):
        return "sources"

    @property
    def buildables(self):
        yield from [
            WorkspacePythonSource(workspace=self.config.workspace, source=source)
            for source in self.config.sources
        ]


class DependencyBuilder(SourceBuilder):
    @property
    def name(self):
        return "dependencies"

    @property
    def buildables(self):
        yield from [
            DependencyInstaller(config=self.config, dependency=dependency)
            for dependency in self.config.dependencies
        ]

    def _build(self, dependency: DependencyInstaller, command: BuildCommand):
        return dependency(force=command.force, logger=self._logger)


class ToolBuilder(DependencyBuilder):
    @property
    def name(self):
        return "tools"

    @property
    def buildables(self):
        yield from [
            ToolInstaller(config=self.config, dependency=dependency)
            for dependency in self.config.tools
        ]


class BuildGoal(Goal):
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
        return (
            ResourceBuilder(self.config),
            SourceBuilder(self.config),
            DependencyBuilder(self.config),
            ToolBuilder(self.config),
        )

    def clean(self):
        mp_deploy_path = self.config.workspace.get_build_asset_path(is_frozen=False)
        if mp_deploy_path.exists():
            self.info(f"Removing {mp_deploy_path}")
            shutil.rmtree(mp_deploy_path, ignore_errors=True)

        frozen_path = self.config.workspace.get_build_asset_path(is_frozen=True)
        if frozen_path.exists():
            self.info(f"Removing {frozen_path}")
            shutil.rmtree(frozen_path, ignore_errors=True)

    def __call__(self, command: Command):
        goal_command = BuildCommand(**command.params)
        if not goal_command.target:
            self.clean()

        for builder in self.builders:
            if not goal_command.builder or goal_command.builder == builder.name:
                try:
                    builder(goal_command)
                except Exception as e:
                    self._logger.exception(f"Error building {builder.name}: {e}")
                    self.fail(str(e))


class ApplicationBuilderPlugin(Plugin):
    def get_goals(self) -> Tuple[Goal]:
        return (BuildGoal(self.config),)
