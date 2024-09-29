"""
Plugins for installing dependencies and tools on the target device
"""
from dataclasses import dataclass
import logging
import os
from typing import Union
from caiman.config import Command, Config, Dependency, Tool
from caiman.device.handler import DeviceHandler
from pathlib import Path

from caiman.plugins.base import Goal, Plugin, fail, param

_logger = logging.getLogger(__name__)


@dataclass
class InstallCommand:
    dependency: str = param("Name of the dependency: <package>@<version>")
    scope: str = param("Scope of the dependency: {dependencies,tools}", default="dependencies")
    channel: str = param("Channel to install the dependency from", default="")
    target: str = param("Target directory to install the dependency to relative to package directory", default="")

    @property
    def package(self):
        return self.dependency.split("@")[0]

    @property
    def version(self):
        return self.dependency.split("@")[1] if "@" in self.dependency else None


class InstallGoal(Goal):
    def __init__(self, config: Config, device: DeviceHandler):
        self.config = config
        self._device = device

    @property
    def help(self):
        return "Install a dependency or tool in the local workspace"

    @property
    def name(self):
        return "install"

    def get_schema(self):
        return InstallCommand

    def _install(self, parent, name, version, target, index):
        _logger.info(f"Installing {name} ({version}) to {target}")
        mount_path = str(Path(self.config.root_path) / parent)
        os.makedirs(mount_path, exist_ok=True)
        cmd = [
            'mip', '--no-mpy', '--index', index, 
            '--target', target,
            'install', f'{name}@{version}'
        ]

        return self._device.run_mp_remote_cmd(*cmd, mount_path=mount_path)

    def install(self, dep: Union[Dependency, Tool]):
        parent = self.config.workspace.tools if isinstance(dep, Tool) else self.config.workspace.packages
        channel = self.config.get_channel(dep.channel)
        remote_target = dep.target or '/'
        remote_target = "/remote" + remote_target

        if not dep.manifest:
            return self._install(
                parent=parent,
                name=dep.name,
                version=dep.version,
                target=remote_target,
                index=channel.index
            )
        else:
            for file_name in dep.manifest:
                install_path = Path(dep.target or '') / file_name
                file_target = install_path.parent
                file_target.mkdir(parents=True, exist_ok=True)

                self._install(
                    parent=parent,
                    name=f"{dep.name}/{file_name}",
                    index=channel.index, 
                    target=str(file_target),
                    version=dep.version
                )

    def __call__(self, command: Command):
        command = InstallCommand(**command.params)
        if not command.version:
            fail(f"Dependency version is required. Use the format <package>@<version>")

        kwargs = dict(name=command.package, version=command.version, target=command.target)
        if command.channel:
            kwargs["channel"] = command.channel

        dep = Dependency(**kwargs) if command.scope != "tools" else Tool(**kwargs)
        return self.install(dep)


class MIPInstallerPlugin(Plugin):
    def __init__(self, config: Config):
        super().__init__(config)
        self._device = DeviceHandler(config=config)

    def install(self, dep: Union[Dependency, Tool]):
        return InstallGoal(config=self.config, device=self._device).install(dep)

    def get_goals(self):
        return [InstallGoal(config=self.config, device=self._device)]




    
