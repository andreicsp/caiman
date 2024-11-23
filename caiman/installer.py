"""
Wrappers for package managers to install dependencies and tools
"""
import logging
from dataclasses import dataclass
from pathlib import Path

from caiman.config import Config, Dependency
from caiman.manifest import (
    DependencyManifestRegistry,
    Manifest,
    ManifestItem,
    ToolManifestRegistry,
)
from caiman.proc.base import MicroPythonProcess
from caiman.proc.local import LocalMicroPythonProcess
from caiman.source import (
    WorkspaceDependencySource,
    WorkspaceSource,
    WorkspaceToolSource,
)
from caiman.task import MIPTask, MoveTask

_logger = logging.getLogger(__name__)


@dataclass(frozen=True, eq=True)
class DependencyInstaller:
    """
    Models a dependency installation process
    """
    config: Config
    dependency: Dependency

    @property
    def workspace(self):
        return self.config.workspace

    @property
    def artifact_root(self):
        """
        Dependency files initially installed to a temporary artifact directory
        that is later scanned for building a manifest of the installed files
        """
        return (
            self.workspace.get_artifact_path("dependencies")
            / self.dependency.package_name
        )

    @property
    def install_root(self):
        """
        Local package installation directory where installed artifacts are moved
        after a manifest is created
        """
        return self.workspace.get_package_path()

    @property
    def manifests(self):
        """
        The manifest registry for the installed dependencies
        """
        return DependencyManifestRegistry(workspace=self.workspace, asset_type="source")

    @property
    def source(self) -> WorkspaceSource:
        """
        Models the sources of the installed dependency
        """
        return WorkspaceDependencySource(
            workspace=self.workspace, source=self.dependency
        )

    def create_manifest(self):
        """
        Scans the artifact directory where the dependency was installed to create a manifest
        that will be used to track the installed files and copy them to the local package directory
        """
        files = [
            p.relative_to(self.artifact_root)
            for p in Path(self.artifact_root).rglob("**/*")
            if p.is_file()
        ]
        items = ManifestItem.from_paths(files, self.artifact_root)
        return Manifest(
            name=self.dependency.package_name,
            version=self.dependency.version,
            items=items,
        )

    def get_tasks(self):
        """
        Get the tasks for installing the dependency.
        These will include a package installation task for each asset in the dependency
        """
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
        packages_by_target = {}
        for name, target in zip(install_names, install_targets):
            packages_by_target.setdefault(target, {})[name] = self.dependency.version

        for target, packages in packages_by_target.items():
            yield from MIPTask.from_package_dict(
                workspace=self.workspace,
                packages=packages,
                index=channel.index,
                root=self.artifact_root,
                target=target,
            )

    @property
    def handler(self) -> MicroPythonProcess:
        """
        The handler for the MicroPython package manager used to install the dependency
        """
        return LocalMicroPythonProcess()

    def install(self, force=False, logger=None):
        """
        Install the dependency.
        A manifest is created for the installed files and saved to the manifest registry
        The installed files are then moved to the local package directory

        :param force: Force the installation even if the dependency is already installed
        :param logger: The logger to use for logging installation output
        """
        logger = logger or _logger
        manifest = self.manifests.get(self.dependency.package_name)
        if manifest and manifest.version == self.dependency.version and not force:
            logger.info(
                f"Dependency {self.dependency.name} ({self.dependency.version}) is already installed"
            )
            return manifest

        for task in self.get_tasks():
            logger.info(f"{task}")
            out = task(device=self.handler)
            logger.info(out.decode())

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
        source = self.source
        deployment = source.create_deployment()
        if deployment:
            deployment(logger=logger)


@dataclass(frozen=True, eq=True)
class ToolInstaller(DependencyInstaller):
    """
    Models a tool installation process
    Tools are only installed to the tools directory and are not uploaded to the device
    """
    @property
    def artifact_root(self):
        return self.workspace.get_artifact_path("tools") / self.dependency.package_name

    @property
    def install_root(self):
        return self.workspace.get_tool_path()

    @property
    def manifests(self):
        return ToolManifestRegistry(workspace=self.workspace, asset_type="source")

    @property
    def source(self) -> WorkspaceSource:
        return WorkspaceToolSource(workspace=self.workspace, source=self.dependency)
