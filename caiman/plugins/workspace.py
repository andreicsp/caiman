import logging

from caiman.config import DEFAULT_CONF_FILE, Command, Config, get_project_init_fields

from caiman.plugins.base import Goal, Plugin, fail
import dataclasses

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
        else:
            _logger.info(f"Updating config file: {DEFAULT_CONF_FILE}")

        _logger.info("Project details:")
        app = _updated_config_from_input(self.config.application)
    
        _logger.info("Workspace structure:")
        workspace = _updated_config_from_input(self.config.workspace)
        self.config = dataclasses.replace(
            self.config, 
            application=app,
            workspace=workspace
        )
        self.config.save(path=DEFAULT_CONF_FILE)
        _logger.info(f"Config file created: {DEFAULT_CONF_FILE}")


class WorkspacePlugin(Plugin):
    """
    Plugin to handle configuration files
    """
    def get_goals(self):
        return (WorkspaceInitGoal(config=self.config),)


def _updated_config_from_input(config: Config):
    init_fields = get_project_init_fields(config)
    update_dict = {}
    for init_field in init_fields:
        current_value = getattr(config, init_field.name)
        new_value = input(f"{init_field.metadata['label']} [{current_value}]:") or current_value
        update_dict[init_field.name] = new_value

    return dataclasses.replace(config, **update_dict)