import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

from caiman.config import Workspace
from caiman.manifest import Manifest, SourceManifestRegistry, \
    DependencyManifestRegistry, ToolManifestRegistry, ResourceManifestRegistry, ManifestItem
from caiman.task import Task, CopyTask, CompileTask

_logger = logging.getLogger(__name__)


@dataclass(frozen=True, eq=True)
class Deployment:
    source_path: Path
    source_manifest: Manifest
    workspace: Workspace
    is_frozen: bool
    compile: bool

    @property
    def manifests(self):
        return ResourceManifestRegistry(
            workspace=self.workspace,
            asset_type="target",
        )

    @property
    def path(self) -> Path:
        """
        The root directory of the target files."""
        return self.workspace.get_build_asset_path(is_frozen=self.is_frozen)

    def get_tasks(self) -> Iterator[Task]:
        """
        Generator for the source and target file paths."""
        for source_item in self.source_manifest.items:
            source_path = self.source_path / source_item.path
            
            target_path = self.path / Path(source_item.path)
            if target_path.suffix == ".py" and self.compile:
                target_path = target_path.with_suffix(".mpy")
                yield CompileTask(
                    source_file=source_path,
                    target_file=target_path,
                    workspace=self.workspace,
                )
            else:
                yield CopyTask(
                    source_file=source_path,
                    target_file=target_path,
                    workspace=self.workspace,
                )

    def __iter__(self) -> Iterator[Path]:
        """
        The manifest items for the target files."""
        for task in self.get_tasks():
            yield task.target_file.relative_to(self.path)

    def __call__(self, logger=None):
        logger = logger or _logger
        items = []
        for task in self.get_tasks():
            logger.info(f"{task}")
            target_file = task()
            rel_path = target_file.relative_to(self.path)
            items.append(ManifestItem.create(rel_path, self.path))

        return Manifest(
            name=self.source_manifest.name,
            version=self.source_manifest.version,
            items=items,
        )



@dataclass(frozen=True, eq=True)
class PythonDeployment(Deployment):
    @property
    def manifests(self):
        return SourceManifestRegistry(
            workspace=self.workspace,
            asset_type="target",
        )


@dataclass(frozen=True, eq=True)
class DependencyDeployment(Deployment):
    @property
    def manifests(self):
        return DependencyManifestRegistry(
            workspace=self.workspace,
            asset_type="target",
        )


@dataclass(frozen=True, eq=True)
class ToolDeployment(Deployment):
    @property
    def manifests(self):
        return ToolManifestRegistry(
            workspace=self.workspace,
            asset_type="target",
        )