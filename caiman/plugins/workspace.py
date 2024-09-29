import logging

from dacite import Config
from caiman.config import DEFAULT_CONF_FILE, Command
from caiman.plugins.base import Goal, Plugin, fail
import dataclasses
import yaml

_logger = logging.getLogger(__name__)


@dataclasses.dataclass
class WorkspaceCommand:
    pass


class WorkspaceInitGoal(Goal):
    def __init__(self, config: Config):
        self.config = config

    @property
    def help(self):
        return "Initialize a new workspace"
  
    @property
    def name(self):
        return "init"

    def get_schema(self):
        return WorkspaceCommand

    def __call__(self, command: Command):
        if DEFAULT_CONF_FILE.exists() and not command.force:
            fail("Config file already exists")
        
        _logger.info(f"Creating config file: {DEFAULT_CONF_FILE}")
        _logger.info("Project details:")
        firmware = self.config.firmware
        firmware.name = input(f"Project name [{firmware.name}]:") or firmware.name
        firmware.version = input(f"Project version [{firmware.version}]:") or firmware.version
        firmware.author = input(f"Author [{firmware.author}]:") or firmware.author

        _logger.info("Workspace structure:")
        workspace = self.config.workspace
        workspace.build = input(f"Build directory [{workspace.build}]:") or workspace.build
        workspace.sources = input(f"Sources directory [{workspace.sources}]:") or workspace.sources
        workspace.packages = input(f"Local MIP package directory [{workspace.packages}]:") or workspace.packages

        with open(DEFAULT_CONF_FILE, "w") as f:
            d = dataclasses.asdict(self.config)
            d.pop("root_path", None)
            yaml.dump(d, f, sort_keys=False)

        _logger.info(f"Config file created: {DEFAULT_CONF_FILE}")


class WorkspacePlugin(Plugin):
    """
    Plugin to handle configuration files
    """
    def get_goals(self):
        return (WorkspaceInitGoal(config=self.config),)
