"""
The manifest module provides classes for collecting and tracking manifests of files that
compose a build target.
Manifests are generated for resources, sources, dependencies, and tools.
"""
import json
from dataclasses import asdict, dataclass, field
from hashlib import sha1
from pathlib import Path
from typing import List

import dacite

from caiman.config import Workspace


@dataclass(frozen=True, eq=True)
class ManifestItem:
    """
    Class for defining a file in a manifest. All paths are relative as manifests can be interpreted
    in different contexts (e.g: temporary artifact locations, local package directories, etc.)
    """
    path: str
    sha1: str
    size: int

    @classmethod
    def create(cls, relative_path: Path, source_root: Path):
        """
        Create a manifest item from a relative path and source root.
        :param relative_path: The relative path of the file.
        :param source_root: The root directory of the source to which the path is relative.
        """
        return cls(
            path=str(relative_path),
            sha1=str(sha1(Path(source_root / relative_path).read_bytes()).hexdigest()),
            size=Path(source_root / relative_path).stat().st_size,
        )

    @classmethod
    def from_paths(cls, paths: List[Path], source_root: Path):
        """
        Create a list of manifest items from a list of relative paths and source root.
        :param paths: The list of relative paths of the files.
        :param source_root: The root directory of the source to which the paths are relative.
        """
        return [cls.create(path, source_root) for path in paths]

    def is_file_changed(self, path: Path) -> bool:
        """
        Check if the file tracked by this manifest item has changed with respect to the file at the given path.
        """
        return (
            not path.exists()
            or self.size != path.stat().st_size
            or self.sha1 != sha1(path.read_bytes()).hexdigest()
        )


@dataclass(frozen=True, eq=True)
class Manifest:
    """
    Class for defining a manifest of files that compose a build target.
    """
    name: str
    version: str = ""
    items: List[ManifestItem] = field(default_factory=list)

    def __iter__(self):
        return (Path(item.path) for item in self.items)


@dataclass(frozen=True, eq=True)
class ManifestRegistry:
    """
    Class for defining a registry of manifests for a particular asset type.
    Asset types include source code, and target files
    """
    workspace: Workspace
    asset_type: str = "source"

    @property
    def folder(self) -> str:
        """
        Parent folder for the manifest files. This is used to organize the manifest files for different
        types of build targets.
        """
        return ""

    def get_manifest_path(self, package: str) -> Path:
        """
        Get the path to the manifest file for the source files.
        :param package: The name of the package for which the manifest is being created.
        """
        base_name = f"{package}-{self.asset_type}.json"
        return self.workspace.get_manifest_path(self.folder) / base_name

    def get(self, package: str) -> Manifest:
        """
        Load the manifest for the source files.
        :param package: The name of the package for which the manifest is being created.
        """
        path = self.get_manifest_path(package)
        if path.exists():
            json_manifest = json.loads(path.read_text()).get(package, {})
            return dacite.from_dict(
                data_class=Manifest,
                data=dict(parent=self.folder, name=package, **json_manifest),
            )

    def save(self, manifest: Manifest):
        """
        Save the manifest for the source files.
        """
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
    """
    Class for defining a registry of manifests for the installed dependencies.
    """
    @property
    def folder(self) -> str:
        return "dependencies"


@dataclass(frozen=True, eq=True)
class SourceManifestRegistry(ManifestRegistry):
    """
    Class for defining a registry of manifests for the source files.
    """
    @property
    def folder(self) -> str:
        return "sources"


@dataclass(frozen=True, eq=True)
class ResourceManifestRegistry(ManifestRegistry):
    """
    Class for defining a registry of manifests for the resource files.
    """
    @property
    def folder(self) -> str:
        return "resources"


@dataclass(frozen=True, eq=True)
class ToolManifestRegistry(ManifestRegistry):
    """
    Class for defining a registry of manifests for the tools.
    """
    @property
    def folder(self) -> str:
        return "tools"
