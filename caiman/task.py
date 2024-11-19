import subprocess
import sys
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path

from caiman.config import Workspace
from caiman.device.handler import DeviceHandler


@dataclass(frozen=True, eq=True)
class Task(ABC):
    """
    Class for defining a copy task between two paths.
    """
    workspace: Workspace
    @abstractmethod
    def __call__(self, *args, **kwargs):
        pass


@dataclass(frozen=True, eq=True)
class CopyTask(Task):
    source_file: Path
    target_file: Path

    @property
    def rel_source_path(self) -> Path:
        """
        The relative source path."""
        return self.workspace.get_relative_path(self.source_file)

    @property
    def rel_target_path(self) -> Path:
        """
        The relative target path."""
        return self.workspace.get_relative_path(self.target_file)

    def __call__(self, *args, **kwargs):
        self.target_file.parent.mkdir(parents=True, exist_ok=True)
        self.target_file.write_bytes(self.source_file.read_bytes())
        return self.target_file

    def __str__(self):
        return f"[{self.__class__.__name__}] {self.rel_source_path} -> {self.rel_target_path}"

@dataclass(frozen=True, eq=True)
class MoveTask(CopyTask):
    def __call__(self, *args, **kwargs):
        self.target_file.parent.mkdir(parents=True, exist_ok=True)
        self.source_file.rename(self.target_file)
        return self.target_file


@dataclass(frozen=True, eq=True)
class CompileTask(CopyTask):
    """
    Class for defining a compile task between two paths.
    """
    def __call__(self, *args, **kwargs):
        self.target_file.parent.mkdir(parents=True, exist_ok=True)
        command = [
            sys.executable, "-m", "mpy_cross_v6",
            str(self.source_file), "-o", str(self.target_file),
        ]
        subprocess.run(command, check=True, stderr=subprocess.PIPE)
        return self.target_file


@dataclass(frozen=True, eq=True)
class MIPTask(Task):
    """
    Class for defining a MIP task between two paths.
    """
    index: str
    packages: list
    root: Path
    target: Path = ''

    def __call__(self, *args, device: DeviceHandler, **kwargs):
        target = "/remote"
        if self.target:
            target += f"/{self.target}"

        command = [
            "mip", "--no-mpy",
            "--index", self.index,
            "--target", str(target),
            "install"] + self.packages
        local_parent = self.root / self.target
        local_parent.mkdir(parents=True, exist_ok=True)
        return device.run_mp_remote_cmd(*command, mount_path=str(self.root))

    @classmethod
    def from_package_dict(cls, packages: dict, workspace: Workspace, index: str, root: Path, target: Path):
        return [MIPTask(
            workspace=workspace,
            index=index,
            packages=[f"{k}@{v}" for k, v in packages.items()],
            root=root,
            target=target,
        )]

    def __str__(self):
        local_target = self.root / self.target
        package_info = ", ".join(self.packages)
        return f"[{self.__class__.__name__}] {package_info} -> {local_target}"
