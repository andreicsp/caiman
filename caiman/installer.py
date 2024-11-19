import logging
from dataclasses import dataclass
from pathlib import Path

from caiman.config import Workspace, Dependency, Config
from caiman.device.handler import DeviceHandler
from caiman.manifest import DependencyManifestRegistry, ManifestItem, Manifest, ToolManifestRegistry
from caiman.source import WorkspaceSource, WorkspaceDependencySource, WorkspaceToolSource
from caiman.task import MIPTask, CopyTask, MoveTask

_logger = logging.getLogger(__name__)

@dataclass(frozen=True, eq=True)
class DependencyInstaller:
    config: Config
    dependency: Dependency

    @property
    def workspace(self):
        return self.config.workspace

    @property
    def artifact_root(self):
        return self.workspace.get_artifact_path("dependencies") / self.dependency.package_name

    @property
    def install_root(self):
        return self.workspace.get_package_path()

    @property
    def manifests(self):
        return DependencyManifestRegistry(workspace=self.workspace, asset_type="source")

    def get_source(self) -> WorkspaceSource:
        return WorkspaceDependencySource(workspace=self.workspace, source=self.dependency)

    def create_manifest(self):
        files = [p.relative_to(self.artifact_root) for p in Path(self.artifact_root).rglob("**/*") if p.is_file()]
        items = ManifestItem.from_paths(files, self.artifact_root)
        return Manifest(
            name=self.dependency.package_name,
            version=self.dependency.version,
            items=items,
        )

    def get_tasks(self):
        channel = self.config.get_channel(self.dependency.channel)

        install_names = (
            [self.dependency.name]
            if not self.dependency.files
            else [f"{self.dependency.name}/{f}" for f in self.dependency.files]
        )
        install_targets = (
            [Path("")]
            if not self.dependency.files
            else [Path(f).parent for f in self.dependency.files]
        )
        names_by_target = {}
        for name, target in zip(install_names, install_targets):
            names_by_target.setdefault(target, []).append(f"{name}@{self.dependency.version}")

        for target, names in names_by_target.items():
            yield MIPTask(
                workspace=self.workspace,
                packages=names,
                index=channel.index,
                root=self.artifact_root,
                target=target,
            )

    def install(self, force=False, logger=None):
        logger = logger or _logger
        manifest = self.manifests.get(self.dependency.package_name)
        if manifest and manifest.version == self.dependency.version and not force:
            logger.info(f"Dependency {self.dependency.name} ({self.dependency.version}) is already installed")
            return manifest

        device = DeviceHandler(self.config)

        for task in self.get_tasks():
            logger.info(f"{task}")
            task(device=device)

        manifest = self.create_manifest()
        self.manifests.save(manifest)

        for item in manifest.items:
            task = MoveTask(
                source_file=self.artifact_root / item.path,
                target_file=self.install_root / item.path,
                workspace=self.workspace,
            )
            logger.info(f"{task}")
            task()

        return manifest

    def __call__(self, force=False, logger=None):
        logger = logger or _logger
        self.install(force=force, logger=logger)
        source = self.get_source()
        deployment = source.create_deployment()
        if deployment:
            deployment(logger=logger)


@dataclass(frozen=True, eq=True)
class ToolInstaller(DependencyInstaller):
    @property
    def artifact_root(self):
        return self.workspace.get_artifact_path("tools") / self.dependency.package_name

    @property
    def install_root(self):
        return self.workspace.get_tool_path()

    @property
    def manifests(self):
        return ToolManifestRegistry(workspace=self.workspace, asset_type="source")

    def get_source(self) -> WorkspaceSource:
        return WorkspaceToolSource(workspace=self.workspace, source=self.dependency)
