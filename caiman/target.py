"""
Module for defining the target artifacts and sources for a workspace.
"""


from dataclasses import asdict, dataclass
from hashlib import sha1
import json
from pathlib import Path

import dacite
from pathspec import PathSpec

from caiman.config import FileSource, Manifest, ManifestItem, Workspace


@dataclass(frozen=True, eq=True)
class WorkspaceSource:
    """
    Base class for defining a source of files in a workspace.
    """
    workspace: Workspace
    source: FileSource

    def __post_init__(self):
        if Path(self.source.parent).is_absolute():
            raise ValueError(f"Source parent directory path must be relative: {self.source}")

    @property
    def source_root(self) -> Path:
        """
        The root directory of the source files."""
        return self.workspace.get_path(self.source.parent)

    @property
    def target_root(self) -> Path:
        """
        The root directory of the target files."""
        return self.workspace.get_build_path(self.source.container)

    @property
    def ignores(self) -> PathSpec:
        """
        The ignore patterns for the source files."""
        return self.workspace.get_ignore_patterns()

    @property
    def manifest_root(self) -> Path:
        """
        The root directory for the source manifests."""
        return self.workspace.get_build_path("manifests")

    @property
    def manifest_path(self) -> Path:
        """
        The path to the source manifest file."""
        return self.manifest_root / f"{self.source.name}.json"

    @property
    def source_manifest_items(self):
        """
        The manifest items for the source files."""
        for path in self.files():
            yield ManifestItem(
                path=str(path),
                sha1=str(sha1(Path(self.source_root / path)).hexdigest()),
                size=Path(self.source_root / path).stat().st_size
            )

    @property
    def target_manifest_items(self):
        """
        The manifest items for the target files."""
        for _, path in self.copy_tuples():
            relative_path = path.relative_to(self.target_root)
            yield ManifestItem(
                path=str(relative_path),
                sha1=str(sha1(path.read_bytes()).hexdigest()),
                size=path.stat().st_size
            )

    def files(self):
        """
        Generator for the source files."""
        patterns = self.source.files if self.source.files else ["**/*"]
        for pattern in patterns:
            for path in Path(self.source_root).rglob(pattern):
                if not self.ignores or not self.ignores.match_file(str(path)):
                    yield path.relative_to(self.source_root)

    def copy_tuples(self):
        """
        Generator for the source and target file paths."""
        for path in self.files():
            target_path = path
            if target_path.suffix in self.source.suffix_map:
                target_path = target_path.with_suffix(self.source.suffix_map[target_path.suffix])
            yield self.source_root / path, self.target_root / target_path

    def create_manifest(self) -> Manifest:
        """
        Create a manifest for the source files."""
        return Manifest(items=list(self.source_manifest_items), name=self.source.name)

    def create_target_manifest(self) -> Manifest:
        """
        Create a manifest for the target files."""
        return Manifest(items=list(self.target_manifest_items), name=self.source.name)

    def load_manifest(self) -> Manifest:
        """
        Load the manifest for the source files."""
        if self.manifest_path.exists():
            json_manifest = json.loads(self.manifest_path.read_text()).get(self.name, {})
        else:
            json_manifest = {}
        return dacite.from_dict(data_class=Manifest, data=dict(name=self.source.name, **json_manifest))

    def save_manifest(self, manifest: Manifest) -> None:
        """
        Save the manifest for the source files."""
        if not self.manifest_root.exists():
            self.manifest_root.mkdir(parents=True)
        manifest_dict = asdict(manifest)
        json_dict = {manifest_dict.pop("name"): manifest_dict}
        self.manifest_path.write_text(json.dumps(json_dict, indent=2))


@dataclass(frozen=True, eq=True)
class WorkspaceArtifact(WorkspaceSource):
    """
    Base class for defining an artifact in a workspace.
    An artifact is a temporary file or directory that is generated during the build process.
    """
    @property
    def artifact_root(self) -> Path:
        return self.workspace.get_path("artifacts")

    @property
    def manifest_root(self) -> Path:
        return super().manifest_root / "artifacts"

    @property
    def source_path(self) -> Path:
        return self.artifact_root / self.source.name

    @property
    def target_path(self) -> Path:
        return self.workspace.get_build_path(self.source.container)

    @property
    def ignores(self) -> PathSpec:
        return None


@dataclass(frozen=True, eq=True)
class WorkspaceDependencyArtifact(WorkspaceArtifact):
    """
    Class for defining a dependency artifact in a workspace.
    A dependency artifact is a package that is downloaded and installed as a dependency.
    """
    @property
    def artifact_root(self) -> Path:
        return super().artifact_root / "dependencies"
    
    @property
    def manifest_root(self) -> Path:
        return super().manifest_root / "dependencies"

    @property
    def target_path(self) -> Path:
        return self.workspace.get_package_path()


@dataclass(frozen=True, eq=True)
class WorkspaceToolArtifact(WorkspaceSource):
    @property
    def artifact_root(self) -> Path:
        return super().artifact_root / "tools"

    @property
    def target_path(self) -> Path:
        return self.workspace.get_tool_path()

    @property
    def manifest_root(self) -> Path:
        return super().manifest_root / "tools"


@dataclass(frozen=True, eq=True)
class WorkspaceDependencySource(WorkspaceSource):
    def files(self):
        return [item.path for item in self.load_manifest().items]

    @property
    def source_path(self) -> Path:
        return self.workspace.get_package_path(self.source.name)

    @property
    def target_path(self) -> Path:
        return self.workspace.get_build_path(self.source.container)

    @property
    def ignores(self) -> PathSpec:
        return None

    @property
    def manifest_root(self) -> Path:
        return super().manifest_root / "dependencies"