"""
Data models for Caiman configuration artifacts.
"""
import os
from dataclasses import asdict, dataclass, field, fields
from functools import lru_cache
from pathlib import Path
from typing import List

import dacite
import pathspec
import yaml

IGNORES = [
    ".git",
    ".vscode",
    "**/__pycache__",
    "**/*.pyc",
]


DEFAULT_CONF_FILE = Path.cwd() / "caiman.yaml"


def config_field(
    default=IGNORES,
    default_factory=IGNORES,
    label=None,
    project_init=False,
    metadata=None,
):
    """
    A dataclass field with metadata for configuration that can be parsed by the
    project initialization command.
    """
    metadata = metadata or {}
    metadata["label"] = label
    metadata["project_init"] = project_init
    if default is not IGNORES:
        return field(default=default, metadata=metadata)
    if default_factory is not IGNORES:
        return field(default_factory=default_factory, metadata=metadata)


def get_field_label(field):
    """
    Get the label for the given field from the project initialization goal
    """
    return field.metadata.get("label", field.name)


def get_project_init_fields(cls):
    return [f for f in fields(cls) if f.metadata.get("project_init")]


@dataclass
class Command:
    """
    Models a high level command from the command line interface.
    """
    goal: str
    params: dict = field(default_factory=dict)
    force: bool = False


@dataclass
class Application:
    """
    Models the project application metadata.
    """
    name: str = config_field("", label="Project name", project_init=True)
    version: str = config_field("0.0.1", label="Project version", project_init=True)
    author: str = config_field("", label="Author", project_init=True)


@dataclass
class Device:
    """
    Configuration for working with a device.
    """
    port: str = ""


@lru_cache
def get_ignore_patterns(root: str) -> pathspec.PathSpec:
    """
    Get the ignore patterns for the .gitignore file in the workspace root.
    """
    ignore_file = Path(root) / ".gitignore"
    if ignore_file.exists():
        lines = ignore_file.read_text().splitlines()
        return pathspec.gitignore.GitIgnoreSpec.from_lines(lines)


class ConfigElement:
    """
    Base class for configuration elements.
    """
    def validate(self):
        pass


@dataclass(frozen=True, eq=True)
class Workspace(ConfigElement):
    """
    Configuration for the project workspace
    Includes paths for build, packages, tools, and plugins as a list of additional
    user-defined plugins for the build system
    """
    root: str
    build: str = config_field("build/board", label="Build directory", project_init=True)
    packages: str = config_field(
        "venv/mip-packages", label="Local MIP package directory", project_init=True
    )
    tools: str = config_field(
        "venv/tools", label="Local tools directory", project_init=True
    )
    plugins: List[str] = field(default_factory=list)
    extra_ignores: List[str] = field(default_factory=lambda: IGNORES)
    use_gitignore: bool = True

    def validate(self):
        """
        Validate the workspace configuration
        """
        for path in [
            self.get_path(),
            self.get_build_path(),
            self.get_package_path(),
            self.get_tool_path(),
        ]:
            if not path.is_relative_to(self.root):
                raise ValueError(f"Path {path} must be relative to workspace root")

    def get_path(self, folder: str = "") -> Path:
        """
        Get the full path to a folder in the workspace.
        """
        if Path(folder).is_absolute():
            raise ValueError(f"Folder path {folder} must not be absolute")
        return Path(self.root) / folder

    def get_build_path(self, folder: str = "") -> Path:
        """
        Get the full path to a folder in the build directory
        """
        return self.get_path(self.build) / folder

    def get_artifact_path(self, folder: str = "") -> Path:
        """
        Get the full path to a folder in the artifacts directory used by plugins
        to store temporary build artifacts.
        """
        return self.get_build_path("artifacts") / folder

    def get_manifest_path(self, folder: str = "") -> Path:
        """
        Get the full path to a folder in the manifests directory
        """
        return self.get_build_path("manifests") / folder

    def get_build_asset_path(self, is_frozen: bool, folder: str = "") -> Path:
        """
        Get the full path to a folder in the build directory for frozen or deployable assets.
        """
        return self.get_build_path("frozen" if is_frozen else "micropython") / folder

    def get_package_path(self, folder: str = "") -> Path:
        """
        Get the full path to a folder in the local packages directory. Dependencies
        are locally installed in this directory.
        """
        return self.get_path(self.packages) / folder

    def get_tool_path(self, folder: str = "") -> Path:
        """
        Get the full path to a folder in the local tools directory. Tools are locally
        installed in this directory.
        """
        return self.get_path(self.tools) / folder

    def get_ignore_patterns(self) -> pathspec.PathSpec:
        """
        Get the ignore patterns for the workspace by combining the .gitignore file
        patterns with the extra ignore patterns.
        """
        patterns = pathspec.gitignore.GitIgnoreSpec.from_lines(self.extra_ignores)
        root_patterns = get_ignore_patterns(self.root)
        if root_patterns:
            patterns = root_patterns + patterns
        return patterns

    def get_relative_path(self, path: Path) -> Path:
        """
        Get the relative path to a file or directory in the workspace.
        """
        if not path.is_relative_to(self.root):
            raise ValueError(f"Path {path} is not relative to workspace root")
        return path.relative_to(self.root)


@dataclass(frozen=True, eq=True)
class Channel(ConfigElement):
    """
    Configuration for a package channel.
    """
    name: str = "micropython"
    index: str = "https://micropython.org/pi/v2"


def default_channels():
    return [Channel()]


@dataclass(frozen=True, eq=True)
class Target(ConfigElement):
    """
    Base class for build targets.
    """
    name: str

    def to_dict(self):
        return asdict(self)

    @property
    def container(self):
        return None

    @property
    def is_frozen(self):
        return False


@dataclass(frozen=True, eq=True)
class PythonTarget(Target):
    """
    Base class for Python build targets.
    """
    frozen: bool = False
    compile: bool = True

    @property
    def is_frozen(self):
        return self.frozen


@dataclass(frozen=True, eq=True)
class FileSource(Target):
    """
    Base class for file sources.
    """
    files: List[str] = field(default_factory=list)
    parent: str = ""
    version: str = ""

    @property
    def package_name(self):
        return os.path.join(*self.name.split(":"))

    @property
    def container(self):
        return "micropython"

    def validate(self):
        if Path(self.parent).is_absolute():
            raise ValueError(f"Parent path {self.parent} must be relative")
        for file in self.files:
            if Path(file).is_absolute():
                raise ValueError(f"File path {file} must be relative")


def _default_python_path_patterns():
    return ["**/*.py"]


@dataclass(frozen=True, eq=True)
class PythonSource(FileSource, PythonTarget):
    """
    Configuration for a Python source.
    """
    files: List[str] = field(default_factory=_default_python_path_patterns)

    @classmethod
    def default_sources(cls):
        return [PythonSource(name="micropython", parent="micropython", compile=True)]

    @property
    def container(self):
        return super().container if not self.frozen else "frozen"


@dataclass(frozen=True, eq=True)
class Dependency(PythonSource):
    name: str
    version: str = "latest"
    channel: str = None
    files: List[str] = field(default_factory=list)


@dataclass
class Config:
    version: str = "0.0.1"
    device: Device = field(default_factory=Device)
    application: Application = field(default_factory=Application)
    workspace: Workspace = field(default_factory=Workspace)
    channels: List[Channel] = field(default_factory=default_channels)
    sources: List[PythonSource] = field(default_factory=PythonSource.default_sources)
    dependencies: List[Dependency] = field(default_factory=list)
    resources: List[FileSource] = field(default_factory=list)
    tools: List[Dependency] = field(default_factory=list)

    @classmethod
    def default(cls) -> "Config":
        return cls(workspace=Workspace(root=str(Path.cwd())))

    @classmethod
    def load(cls, path: str = "") -> "Config":
        path = path or DEFAULT_CONF_FILE
        cfg = yaml.safe_load(open(path)) or {}
        cfg.setdefault("workspace", {})["root"] = str(Path(path).resolve().parent)
        config = dacite.from_dict(data_class=cls, data=cfg)
        config.validate()
        return config

    def validate(self):
        self.workspace.validate()
        for source in self.sources:
            source.validate()
        for dep in self.dependencies:
            dep.validate()
        for res in self.resources:
            res.validate()
        for tool in self.tools:
            tool.validate()

    def save(self, path: str = "") -> None:
        self.validate()
        path = path or DEFAULT_CONF_FILE
        with open(path, "w") as f:
            d = asdict(self)
            d.get("workspace", {}).pop("root", None)
            yaml.dump(d, f, sort_keys=False)

    @property
    def root_path(self):
        return self.workspace.root

    def get_channel(self, name=None) -> Channel:
        if name:
            channel = next((c for c in self.channels if c.name == name), None)
            if not channel:
                raise ValueError(f"Channel {name} not found")
        else:
            channel = self.channels[0]
        return channel
