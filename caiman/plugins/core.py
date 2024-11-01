from caiman.plugins.base import PluginProvider
from caiman.plugins.workspace import WorkspacePlugin


class CorePluginProvider(PluginProvider):
    def get_plugins(self, config):
        from caiman.plugins.builder import ApplicationBuilderPlugin
        from caiman.plugins.deploy import DeployPlugin
        from caiman.plugins.fs import FileSystemPlugin
        from caiman.plugins.installer import MIPInstallerPlugin
        from caiman.plugins.runner import RunnerPlugin

        return [
            WorkspacePlugin(config=config),
            ApplicationBuilderPlugin(config=config),
            DeployPlugin(config=config),
            FileSystemPlugin(config=config),
            RunnerPlugin(config=config),
            MIPInstallerPlugin(config=config),
        ]
