"""
Plugins that upload build artifacts to the target device
"""
from dataclasses import dataclass

from caiman.config import Command, Config
from caiman.device import FileSystem
from caiman.plugins.base import Goal, Plugin
from caiman.proc.device import DeviceMicroPythonProcess


@dataclass
class DeployCommand:
    pass


class DeployGoal(Goal):
    def __init__(self, config: Config, fs: FileSystem):
        super().__init__(config)
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
        mp_root_path = self.config.workspace.get_build_asset_path(is_frozen=False)
        paths = mp_root_path.glob("*")
        for path in paths:
            rel_path = str(path.relative_to(mp_root_path))
            self.info(f"Uploading {rel_path}")
            self._fs.upload(src=rel_path, dst="", cwd=mp_root_path)


class DeployPlugin(Plugin):
    def __init__(self, config: Config):
        super().__init__(config=config)
        self._fs = FileSystem(device=DeviceMicroPythonProcess(config=config.device))

    def get_goals(self):
        return (DeployGoal(config=self.config, fs=self._fs),)
