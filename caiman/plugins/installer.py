"""
Plugins for installing dependencies and tools on the target device
"""
from dataclasses import dataclass
from pathlib import Path

from caiman.config import Command, Config, Dependency
from caiman.device.handler import DeviceHandler
from caiman.plugins.base import Goal, Plugin, fail, param
from caiman.target import (
    WorkspaceArtifact,
    WorkspaceDependencyArtifact,
    WorkspaceSource,
    WorkspaceToolArtifact,
)


@dataclass
class InstallCommand:
    dependency: str = param("Name of the dependency: <package>@<version>")
    scope: str = param(
        "Scope of the dependency: {dependencies,tools}", default="dependencies"
    )
    channel: str = param("Channel to install the dependency from", default="")
    reinstall: bool = param("Reinstall the dependency", default=False)

    @property
    def package(self):
        return self.dependency.split("@")[0]

    @property
    def version(self):
        return self.dependency.split("@")[1] if "@" in self.dependency else None


class InstallGoal(Goal):
    def __init__(self, config: Config, device: DeviceHandler):
        super().__init__(config)
        self.device = device

    @property
    def help(self):
        return "Install a dependency or tool in the local workspace"

    @property
    def name(self):
        return "install"

    def get_schema(self):
        return InstallCommand

    def _mip_install(
        self, name: str, version: str, index: str, install_path: str, target: str = ""
    ):
        self.info(f"Installing {name} ({version}) to {install_path}/{target}")
        remote_root = "/remote"
        target = "/".join([remote_root, target]) if target else remote_root

        cmd = [
            "mip",
            "--no-mpy",
            "--index",
            index,
            "--target",
            str(target),
            "install",
            f"{name}@{version}",
        ]
        return self.device.run_mp_remote_cmd(*cmd, mount_path=install_path)

    def install(
        self, artifact: WorkspaceArtifact, force: bool = False
    ) -> WorkspaceSource:
        parent = artifact.source_root
        channel = self.config.get_channel(artifact.source.channel)
        install_names = (
            [artifact.source.name]
            if not artifact.source.files
            else [f"{artifact.source.name}/{f}" for f in artifact.source.files]
        )
        install_targets = (
            [""]
            if not artifact.source.files
            else [Path(f).parent for f in artifact.source.files]
        )

        current_manifest = artifact.load_manifest()
        if current_manifest.version == artifact.source.version and not force:
            self.info(
                f"Dependency {artifact.source.name} ({artifact.source.version}) is already installed"
            )
            return artifact.workspace_source

        for name, target in zip(install_names, install_targets):
            file_install_path = parent / target
            file_install_path.mkdir(parents=True, exist_ok=True)
            self._mip_install(
                name=name,
                version=artifact.source.version,
                index=channel.index,
                install_path=str(artifact.source_root),
                target=str(target),
            )
        manifest = artifact.create_source_manifest()
        artifact.save_manifest(manifest)

        for copy_task in artifact.get_copy_tasks():
            copy_task.target_file.parent.mkdir(parents=True, exist_ok=True)
            copy_task.target_file.write_bytes(copy_task.source_file.read_bytes())
            copy_task.source_file.unlink()

        # artifact.source_root.rmdir()
        target_root_rel = self.config.workspace.get_relative_path(artifact.target_root)
        self.info(
            f"Dependency {artifact.source.name} ({artifact.source.version}) installed at {target_root_rel}"
        )
        return artifact.workspace_source

    def __call__(self, command: Command):
        command = InstallCommand(**command.params)
        if not command.version:
            fail("Dependency version is required. Use the format <package>@<version>")

        kwargs = dict(name=command.package, version=command.version)
        if command.channel:
            kwargs["channel"] = command.channel

        dep = Dependency(**kwargs)
        if command.scope == "dependencies":
            artifact = WorkspaceDependencyArtifact(
                source=dep, workspace=self.config.workspace
            )
        elif command.scope == "tools":
            artifact = WorkspaceToolArtifact(
                source=dep, workspace=self.config.workspace
            )
        else:
            raise ValueError(f"Invalid scope: {command.scope}")
        self.install(artifact, force=command.reinstall)


class MIPInstallerPlugin(Plugin):
    def __init__(self, config: Config):
        super().__init__(config)
        self.device = DeviceHandler(config=config)

    def install(self, dep: WorkspaceArtifact, force: bool = False) -> WorkspaceSource:
        return InstallGoal(config=self.config, device=self.device).install(
            dep, force=force
        )

    def get_goals(self):
        return [InstallGoal(config=self.config, device=self.device)]
