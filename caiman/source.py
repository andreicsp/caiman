"""
Module for defining the target artifacts and sources for a workspace.
"""

from dataclasses import dataclass
from pathlib import Path

from pathspec import PathSpec

from caiman.config import Dependency, FileSource, PythonSource, Workspace
from caiman.deployment import (
    DependencyDeployment,
    Deployment,
    PythonDeployment,
)
from caiman.manifest import (
    DependencyManifestRegistry,
    Manifest,
    ManifestItem,
    ResourceManifestRegistry,
    SourceManifestRegistry,
    ToolManifestRegistry,
)


@dataclass(frozen=True, eq=True)
class WorkspaceSource:
    """
    Base class for defining a source of files in a workspace.
    """

    workspace: Workspace
    source: FileSource

    def __post_init__(self):
        if Path(self.source.parent).is_absolute():
            raise ValueError(
                f"Source parent directory path must be relative: {self.source}"
            )

    @property
    def name(self):
        """
        The name of the source files."""
        return self.source.name

    @property
    def root(self) -> Path:
        """
        The root directory of the source files."""
        return self.workspace.get_path(self.source.parent)

    @property
    def ignores(self) -> PathSpec:
        """
        The ignore patterns for the source files."""
        return self.workspace.get_ignore_patterns()

    @property
    def manifests(self):
        """
        The registry of manifests for the source files.
        """
        return ResourceManifestRegistry(workspace=self.workspace, asset_type="source")

    def create_manifest(self):
        """
        Create a manifest for the source files.
        """
        return Manifest(
            name=self.source.package_name,
            version=self.source.version,
            items=ManifestItem.from_paths(list(self), self.root),
        )

    def get_manifest(self):
        """
        Get the manifest for the source files.
        """
        return self.manifests.get(self.source.package_name)

    def create_deployment(self):
        """
        Create a deployment for the source files.
        """
        return Deployment(
            source_path=self.root,
            source_manifest=self.get_manifest(),
            workspace=self.workspace,
            is_frozen=self.source.is_frozen,
            compile=False,
        )

    def __iter__(self):
        """
        Generator for the source files."""
        patterns = self.source.files if self.source.files else ["**/*"]
        for pattern in patterns:
            for path in Path(self.root).rglob(pattern):
                if path.is_file():
                    if not self.ignores or not self.ignores.match_file(str(path)):
                        yield path.relative_to(self.root)


@dataclass(frozen=True, eq=True)
class WorkspacePythonSource(WorkspaceSource):
    source: PythonSource

    @property
    def manifests(self):
        return SourceManifestRegistry(workspace=self.workspace, asset_type="source")

    def create_deployment(self):
        """
        Create a deployment for the source files.
        """
        return PythonDeployment(
            source_path=self.root,
            source_manifest=self.get_manifest(),
            workspace=self.workspace,
            is_frozen=self.source.is_frozen,
            compile=self.source.compile,
        )


@dataclass(frozen=True, eq=True)
class WorkspaceDependencySource(WorkspaceSource):
    source: Dependency

    @property
    def ignores(self) -> PathSpec:
        return None

    @property
    def manifests(self):
        return DependencyManifestRegistry(workspace=self.workspace, asset_type="source")

    def __iter__(self):
        return iter(self.get_manifest() or [])

    @property
    def root(self):
        return self.workspace.get_package_path()

    def create_deployment(self):
        """
        Create a deployment for the source files.
        """
        return DependencyDeployment(
            source_path=self.workspace.get_package_path(),
            source_manifest=self.get_manifest(),
            workspace=self.workspace,
            is_frozen=self.source.is_frozen,
            compile=self.source.compile,
        )


@dataclass(frozen=True, eq=True)
class WorkspaceToolSource(WorkspaceDependencySource):
    @property
    def manifests(self):
        return ToolManifestRegistry(workspace=self.workspace, asset_type="source")

    @property
    def root(self) -> Path:
        return self.workspace.get_tool_path()

    def create_deployment(self):
        """
        Create a deployment for the source files.
        """
        return None
