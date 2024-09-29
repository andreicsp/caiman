"""
Plugins that upload build artifacts to the target device
"""
import logging
from caiman.config import Command, Config
from caiman.device.fs import FileSystem
from caiman.device.handler import DeviceHandler
from caiman.plugins.base import Goal, Plugin
from dataclasses import dataclass

from pathlib import Path

_logger = logging.getLogger(__name__)


@dataclass
class DeployCommand:
    pass


class DeployGoal(Goal):
    def __init__(self, config: Config, fs: FileSystem):
        self.config = config
        self._fs = fs

    @property
    def help(self):
        return "Deploy build artifacts to the target device"

    @property
    def name(self):
        return "deploy"

    def get_schema(self):
        return DeployCommand

    def __call__(self, command: Command):
        paths = Path(self.config.workspace.build).glob("*")
        for path in paths:
            firmware_target = path.relative_to(self.config.workspace.build)
            firmware_target = firmware_target.relative_to("/") if firmware_target.is_absolute() else firmware_target
            if path.is_dir():
                firmware_target = firmware_target.parent

            firmware_target = str(firmware_target.as_posix())
            _logger.info(f"Uploading {path} to {firmware_target}")

            firmware_target = "" if firmware_target == "." else firmware_target
            path = path.relative_to(self.config.workspace.build)
            self._fs.upload(src=str(path), dst=firmware_target, cwd=self.config.workspace.build)


class DeployPlugin(Plugin):
    def __init__(self, config: Config):
        super().__init__(config=config)
        self._fs = FileSystem(device=DeviceHandler(config=config))

    def get_goals(self):
        return (DeployGoal(config=self.config, fs=self._fs),)
