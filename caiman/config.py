from dataclasses import dataclass, field
from typing import List
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
class Firmware:
    name: str = ""
    version: str = "0.0.1"
    author: str = ""


@dataclass
class Device:
    port: str = ""


@dataclass
class Workspace:
    build: str = "build/micropython"
    sources: str = "micropython"
    packages: str = "venv/mip-packages"
    tools: str = "build-tools"
    plugins: List[str] = field(default_factory=list)
    ignores: List[str] = field(default_factory=lambda: IGNORES)


@dataclass(frozen=True, eq=True)
class Channel:
    name: str = "micropython"
    index: str = "https://micropython.org/pi/v2"


def default_channels():
    return [Channel()]


@dataclass
class Resource:
    path: str
    target: str
    pattern: str = "**/*"


@dataclass
class Source(Resource):
    compile: bool = True


@dataclass
class Dependency:
    name: str
    version: str
    manifest: List[str] = field(default_factory=list)
    channel: str = None
    target: str = None

    @property
    def package_name(self):
        return self.name.rsplit("/", 1)[-1]


@dataclass
class Tool(Dependency):
    pass


@dataclass
class Config:
    root_path: str
    version: str = "0.0.1"
    device: Device = field(default_factory=Device)
    firmware: Firmware = field(default_factory=Firmware)
    workspace: Workspace = field(default_factory=Workspace)
    channels: List[Channel] = field(default_factory=default_channels)
    sources: List[Source] = field(default_factory=list)
    dependencies: List[Dependency] = field(default_factory=list)
    resources: List[Resource] = field(default_factory=list)
    tools: List[Tool] = field(default_factory=list)

    @classmethod
    def default(cls) -> 'Config':
        return cls(root_path=str(Path.cwd() / DEFAULT_CONF_FILE))

    @classmethod
    def load(cls, path: str = '') -> 'Config':
        path = path or DEFAULT_CONF_FILE
        cfg = yaml.safe_load(open(path)) or {}
        cfg['root_path'] = str(Path(path).resolve().parent)
        return dacite.from_dict(data_class=cls, data=cfg)

    def get_channel(self, name=None) -> Channel:
        if name:
            channel = next((c for c in self.channels if c.name == name), None)
            if not channel:
                raise ValueError(f"Channel {name} not found")
        else:
            channel = self.channels[0]
        return channel
