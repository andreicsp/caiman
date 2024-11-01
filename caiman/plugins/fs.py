from abc import ABC
from dataclasses import dataclass

from caiman.config import Command
from caiman.device.fs import FileSystem
from caiman.device.handler import DeviceHandler
from caiman.plugins.base import Goal, Plugin, param


@dataclass
class FSTargetCommand:
    target: str = param("Target path on the remote device")


class FileSystemGoal(Goal, ABC):
    def __init__(self, fs: FileSystem):
        self.fs = fs

    def get_schema(self):
        return FSTargetCommand


class WalkGoal(FileSystemGoal):
    @property
    def name(self):
        return "walk"

    @property
    def help(self):
        return "Recursively walk the filesystem"

    def __call__(self, command: Command):
        return self.fs.walk(FSTargetCommand(**command.params).target)


class RMTreeGoal(FileSystemGoal):
    @property
    def name(self):
        return "rmtree"

    @property
    def help(self):
        return "Recursively remove a directory"

    def __call__(self, command: Command):
        return self.fs.rmtree(FSTargetCommand(**command.params).target)


class UploadGoal(FileSystemGoal):
    @property
    def name(self):
        return "upload"

    @property
    def help(self):
        return "Upload a file or directory"

    def __call__(self, command: Command):
        return self.fs.upload(FSTargetCommand(**command.params).target)


class GetFileContentsGoal(FileSystemGoal):
    @property
    def name(self):
        return "cat"

    @property
    def help(self):
        return "Get the contents of a file"

    def __call__(self, command: Command):
        return self.fs.get_file_contents(FSTargetCommand(**command.params).target)


class MKDirGoal(FileSystemGoal):
    @property
    def name(self):
        return "mkdir"

    @property
    def help(self):
        return "Create a directory"

    def __call__(self, command: Command):
        return self.fs.mkdir(FSTargetCommand(**command.params).target)


class GetJsonGoal(FileSystemGoal):
    @property
    def name(self):
        return "json.load"

    @property
    def help(self):
        return "Get the contents of a file as JSON"

    def __call__(self, command: Command):
        return self.fs.get_json(FSTargetCommand(**command.params).target)


class FileSystemPlugin(Plugin):
    def __init__(self, config):
        super().__init__(config)
        self._fs = FileSystem(device=DeviceHandler(config=config))

    def get_goals(self):
        return (
            WalkGoal(fs=self._fs),
            RMTreeGoal(fs=self._fs),
            UploadGoal(fs=self._fs),
            MKDirGoal(fs=self._fs),
            GetFileContentsGoal(fs=self._fs),
            GetJsonGoal(fs=self._fs),
        )
