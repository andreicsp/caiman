from dataclasses import asdict, dataclass, field
from functools import lru_cache
from hashlib import sha1
import json
from typing import List
import pathspec
import yaml
import dacite
from pathlib import Path


IGNORES = [
    ".git",
    ".vscode",
    "**/__pycache__",
    "**/*.pyc",
]


DEFAULT_CONF_FILE = Path.cwd() / "caiman.yaml"


@dataclass
class Command:
    goal: str
    params: dict = field(default_factory=dict)
    force: bool = False


@dataclass
class Application:
    name: str = ""
    version: str = "0.0.1"
    author: str = ""


@dataclass
class Device:
    port: str = ""


@lru_cache
def get_ignore_patterns(root: str) -> pathspec.PathSpec:
    ignore_file = Path(root) / ".gitignore"
    if ignore_file.exists():
        lines = ignore_file.read_text().splitlines()
        return pathspec.gitignore.GitIgnoreSpec.from_lines(lines)


class ConfigElement:
    def validate(self):
        pass


@dataclass(frozen=True, eq=True)
class Workspace(ConfigElement):
    root: str
    build: str = "build/board"
    packages: str = "venv/mip-packages"
    tools: str = "venv/tools"
    plugins: List[str] = field(default_factory=list)
    extra_ignores: List[str] = field(default_factory=lambda: IGNORES)
    use_gitignore: bool = True

    def validate(self):
        for path in [self.get_path(), self.get_build_path(), self.get_package_path(), self.get_tool_path()]:
            if not path.is_relative_to(self.root):
                raise ValueError(f"Path {path} must be relative to workspace root")

    def get_path(self, folder: str = '') -> Path:
        if Path(folder).is_absolute():
            raise ValueError(f"Folder path {folder} must not be absolute")
        return Path(self.root) / folder

    def get_build_path(self, folder: str = '') -> Path:
        return self.get_path(self.build) / folder

    def get_build_asset_path(self, is_frozen: bool, folder: str = '') -> Path:
        return self.get_build_path("frozen" if is_frozen else "micropython") / folder

    def get_package_path(self, folder: str = '') -> Path:
        return self.get_path(self.packages) / folder

    def get_tool_path(self, folder: str = '') -> Path:
        return self.get_path(self.tools) / folder

    def get_ignore_patterns(self) -> pathspec.PathSpec:
        patterns = pathspec.gitignore.GitIgnoreSpec.from_lines(self.extra_ignores)
        root_patterns = get_ignore_patterns(self.root)
        if root_patterns:
            patterns = root_patterns + patterns
        return patterns

    def get_relative_path(self, path: Path) -> Path:
        if not path.is_relative_to(self.root):
            raise ValueError(f"Path {path} is not relative to workspace root")
        return path.relative_to(self.root)


@dataclass(frozen=True, eq=True)
class Channel(ConfigElement):
    name: str = "micropython"
    index: str = "https://micropython.org/pi/v2"


def default_channels():
    return [Channel()]


@dataclass(frozen=True, eq=True)
class Target(ConfigElement):
    name: str

    def to_dict(self):
        return asdict(self)

    @property
    def container(self):
        return None

    @property
    def is_frozen(self):
        return False

    @property
    def suffix_map(self):
        return {}


@dataclass(frozen=True, eq=True)
class PythonTarget(Target):
    frozen: bool = False
    compile: bool = True

    @property
    def is_frozen(self):
        return self.frozen

    @property
    def suffix_map(self):
        m = {}
        if self.compile:
            m[".py"] = ".mpy"
        return m


@dataclass(frozen=True, eq=True)
class FileSource(Target):
    files: List[str] = field(default_factory=list)
    parent: str = ""
    version: str = ""

    @property
    def package_name(self):
        return self.name.rsplit("/", 1)[-1]

    @property
    def container(self):
        return "micropython"

    @property
    def manifest_folder(self) -> Path:
        return Path("resources")

    def validate(self):
        if Path(self.parent).is_absolute():
            raise ValueError(f"Parent path {self.parent} must be relative")
        for file in self.files:
            if Path(file).is_absolute():
                raise ValueError(f"File path {file} must be relative")


@dataclass(frozen=True, eq=True)
class PythonSource(FileSource, PythonTarget):
    @classmethod
    def default_sources(cls):
        return [PythonSource(name="micropython", compile=True)]

    @property
    def container(self):
        return super().container if not self.frozen else "frozen"

    @property
    def manifest_folder(self) -> Path:
        return Path("sources")


@dataclass(frozen=True, eq=True)
class Dependency(PythonSource):
    name: str
    version: str = "latest"
    channel: str = None

    @property
    def manifest_folder(self) -> Path:
        return Path("dependencies")


@dataclass(frozen=True, eq=True)
class ManifestItem:
    path: str
    sha1: str
    size: int


@dataclass(frozen=True, eq=True)
class Manifest:
    name: str
    version: str = ''
    items: List[ManifestItem] = field(default_factory=list)

    @classmethod
    def create(cls, package_name: str, version: str, source_root: Path, paths: List[Path]):
        return cls(
            items=[
                ManifestItem(
                    path=str(path),
                    sha1=str(sha1(Path(source_root / path).read_bytes()).hexdigest()),
                    size=Path(source_root / path).stat().st_size
                ) for path in paths
            ],
            name=package_name,
            version=version
        )

    @classmethod
    def load(cls, path: Path, package_name: str):
        """
        Load the manifest for the source files."""
        json_manifest = json.loads(path.read_text()).get(package_name, {}) if path.exists() else {}
        return dacite.from_dict(data_class=Manifest, data=dict(name=package_name, **json_manifest))
    
    def save(self, path: Path):
        """
        Save the manifest for the source files."""
        manifest_dict = asdict(self)
        json_dict = {
            manifest_dict.pop("name"): manifest_dict,
        }
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(json_dict, indent=2))


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
        return cls(root_path=str(Path.cwd() / DEFAULT_CONF_FILE))

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
