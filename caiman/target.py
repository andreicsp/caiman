"""
Module for defining the target artifacts and sources for a workspace.
"""


from dataclasses import dataclass
from pathlib import Path

from pathspec import PathSpec

from caiman.config import Dependency, FileSource, Manifest, Workspace


@dataclass(frozen=True, eq=True)
class CopyTask:
    """
    Class for defining a copy task between two paths.
    """
    source_file: Path
    target_file: Path
    source: FileSource
    workspace: Workspace

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
        return self.workspace.get_build_asset_path(is_frozen=self.source.is_frozen)

    @property
    def ignores(self) -> PathSpec:
        """
        The ignore patterns for the source files."""
        return self.workspace.get_ignore_patterns()

    @property
    def manifest_folder(self) -> Path:
        """
        The relative directory for the source manifests."""
        return self.source.manifest_folder

    @property
    def manifest_root(self) -> Path:
        """
        The root directory for the source manifests."""
        return self.workspace.get_build_path("manifests") / self.manifest_folder

    @property
    def manifest_ext(self) -> str:
        """
        The extension for the source manifests."""
        return ".mpy.json" if self.suffix_map.get(".py") == ".mpy" else ".json"

    @property
    def manifest_path(self) -> Path:
        """
        The path to the source manifest file."""
        return self.manifest_root / f"{self.source.package_name}{self.manifest_ext}"

    def get_target_files(self):
        """
        The manifest items for the target files."""
        for _, path in self.get_copy_tuples():
            yield path.relative_to(self.target_root)

    def get_source_files(self):
        """
        Generator for the source files."""
        patterns = self.source.files if self.source.files else ["**/*"]
        for pattern in patterns:
            for path in Path(self.source_root).rglob(pattern):
                if not self.ignores or not self.ignores.match_file(str(path)):
                    yield path.relative_to(self.source_root)

    @property
    def suffix_map(self):
        return self.source.suffix_map

    def get_copy_tuples(self):
        """
        Generator for the source and target file paths."""
        for path in self.get_source_files():
            target_path = path
            if target_path.suffix in self.suffix_map:
                target_path = target_path.with_suffix(self.suffix_map[target_path.suffix])
            yield self.source_root / path, self.target_root / target_path

    def get_copy_tasks(self):
        """
        Generator for the copy tasks."""
        for source_path, target_path in self.get_copy_tuples():
            yield CopyTask(source_file=source_path, target_file=target_path, source=self.source, workspace=self.workspace)

    def create_manifest(self) -> Manifest:
        """
        Create a manifest for the target files."""
        return Manifest.create(
            package_name=self.source.package_name,
            version=self.source.version,
            source_root=self.target_root,
            paths=list(self.get_target_files())
        )

    def load_manifest(self) -> Manifest:
        """
        Load the manifest for the source files."""
        return Manifest.load(self.manifest_path, package_name=self.source.package_name)

    def save_manifest(self, manifest: Manifest) -> None:
        """
        Save the manifest for the source files."""
        manifest.save(self.manifest_path)


@dataclass(frozen=True, eq=True)
class WorkspaceArtifact(WorkspaceSource):
    """
    Base class for defining an artifact in a workspace.
    An artifact is a temporary file or directory that is generated during the build process.
    """
    source: Dependency

    @property
    def artifact_root(self) -> Path:
        return self.workspace.get_build_path("artifacts")

    @property
    def source_root(self) -> Path:
        return self.artifact_root / self.source.package_name

    @property
    def ignores(self) -> PathSpec:
        return None

    @property
    def suffix_map(self):
        """
        Do not change file extensions for artifacts yet
        """
        return {}

    @property
    def workspace_source(self) -> WorkspaceSource:
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
    def target_root(self) -> Path:
        return self.workspace.get_package_path()

    @property
    def workspace_source(self) -> WorkspaceSource:
        return WorkspaceDependencySource(workspace=self.workspace, source=self.source)


@dataclass(frozen=True, eq=True)
class WorkspaceToolArtifact(WorkspaceArtifact):
    @property
    def artifact_root(self) -> Path:
        return super().artifact_root / "tools"

    @property
    def target_root(self) -> Path:
        return self.workspace.get_tool_path()

    @property
    def manifest_folder(self) -> Path:
        return "tools"


@dataclass(frozen=True, eq=True)
class WorkspaceDependencySource(WorkspaceSource):
    def get_source_manifest(self):
        return WorkspaceDependencyArtifact(workspace=self.workspace, source=self.source).load_manifest()

    def get_source_files(self):
        yield from [Path(item.path) for item in self.get_source_manifest().items]

    @property
    def source_root(self) -> Path:
        return self.workspace.get_package_path()

    @property
    def ignores(self) -> PathSpec:
        return None
