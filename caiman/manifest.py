from abc import abstractmethod
from dataclasses import asdict, dataclass, field
from hashlib import sha1
import json
from pathlib import Path

import dacite

from typing import List

from caiman.config import Workspace


@dataclass(frozen=True, eq=True)
class ManifestItem:
    path: str
    sha1: str
    size: int

    @classmethod
    def create(cls, relative_path: Path, source_root: Path):
        return cls(
            path=str(relative_path),
            sha1=str(sha1(Path(source_root / relative_path).read_bytes()).hexdigest()),
            size=Path(source_root / relative_path).stat().st_size,
        )

    @classmethod
    def from_paths(cls, paths: List[Path], source_root: Path):
        return [cls.create(path, source_root) for path in paths]

    def is_file_changed(self, path: Path) -> bool:
        return (not path.exists() or
                self.size != path.stat().st_size or
                self.sha1 != sha1(path.read_bytes()).hexdigest()
        )


@dataclass(frozen=True, eq=True)
class Manifest:
    name: str
    version: str = ""
    items: List[ManifestItem] = field(default_factory=list)

    def __iter__(self):
        return (Path(item.path) for item in self.items)


@dataclass(frozen=True, eq=True)
class ManifestRegistry:
    workspace: Workspace
    asset_type: str = "source"

    @property
    def folder(self) -> str:
        return ""

    def get_manifest_path(self, package: str) -> Path:
        base_name = f"{package}-{self.asset_type}.json"
        return self.workspace.get_manifest_path(self.folder) / base_name

    def get(self, package: str) -> Manifest:
        """
        Load the manifest for the source files."""
        path = self.get_manifest_path(package)
        if path.exists():
            json_manifest = (
                json.loads(path.read_text()).get(package, {})
            )
            return dacite.from_dict(
                data_class=Manifest,
                data=dict(parent=self.folder, name=package, **json_manifest)
            )

    def save(self, manifest: Manifest):
        manifest_dict = asdict(manifest)
        json_dict = {
            manifest_dict.pop("name"): manifest_dict,
        }
        path = self.get_manifest_path(manifest.name)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(json_dict, indent=2))
        return manifest


@dataclass(frozen=True, eq=True)
class DependencyManifestRegistry(ManifestRegistry):
    @property
    def folder(self) -> str:
        return "dependencies"


@dataclass(frozen=True, eq=True)
class SourceManifestRegistry(ManifestRegistry):
    @property
    def folder(self) -> str:
        return "sources"


@dataclass(frozen=True, eq=True)
class ResourceManifestRegistry(ManifestRegistry):
    @property
    def folder(self) -> str:
        return "resources"


@dataclass(frozen=True, eq=True)
class ToolManifestRegistry(ManifestRegistry):
    @property
    def folder(self) -> str:
        return "tools"