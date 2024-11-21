"""
Plugins for installing dependencies and tools on the target device
"""
from dataclasses import dataclass

from caiman.config import Command, Dependency
from caiman.installer import DependencyInstaller, ToolInstaller
from caiman.plugins.base import Goal, Plugin, fail, param


@dataclass
class InstallCommand:
    dependency: str = param("Name of the dependency: <package>@<version>")
    scope: str = param(
        "Scope of the dependency: {dependencies,tools}", default="dependencies"
    )
    channel: str = param("Channel to install the dependency from", default="")
    reinstall: bool = param("Reinstall the dependency", default=False)

    @property
    def package(self):
        return self.dependency.split("@")[0]

    @property
    def version(self):
        return self.dependency.split("@")[1] if "@" in self.dependency else None


class InstallGoal(Goal):
    @property
    def help(self):
        return "Install a dependency or tool in the local workspace"

    @property
    def name(self):
        return "install"

    def get_schema(self):
        return InstallCommand

    def __call__(self, command: Command):
        command = InstallCommand(**command.params)
        if not command.version:
            fail("Dependency version is required. Use the format <package>@<version>")

        kwargs = dict(name=command.package, version=command.version)
        if command.channel:
            kwargs["channel"] = command.channel

        dep = Dependency(**kwargs)
        if command.scope == "dependencies":
            installer = DependencyInstaller(dependency=dep, config=self.config)
        elif command.scope == "tools":
            installer = ToolInstaller(dependency=dep, config=self.config)
        else:
            raise ValueError(f"Invalid scope: {command.scope}")
        installer(force=command.reinstall, logger=self._logger)


class MIPInstallerPlugin(Plugin):
    def get_goals(self):
        return [InstallGoal(config=self.config)]
