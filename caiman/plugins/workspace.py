import dataclasses
import logging

from caiman.config import DEFAULT_CONF_FILE, Command, Config, get_project_init_fields
from caiman.plugins.base import Goal, Plugin, fail

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
        print(f"Root: {self.config.workspace.root}")
        app = _updated_config_from_input(self.config.application)

        _logger.info("Workspace structure:")
        workspace = _updated_config_from_input(self.config.workspace)
        self.config = dataclasses.replace(
            self.config, application=app, workspace=workspace
        )
        self.config.save(path=DEFAULT_CONF_FILE)
        build_path = self.config.workspace.get_build_path()
        if not build_path.exists():
            build_path.mkdir(parents=True)
            _logger.info(f"Build directory created: {build_path}")

        package_path = self.config.workspace.get_package_path()
        if not package_path.exists():
            package_path.mkdir(parents=True)
            _logger.info(f"Local package directory created: {package_path}")

        tool_path = self.config.workspace.get_tool_path()
        if not tool_path.exists():
            tool_path.mkdir(parents=True)
            _logger.info(f"Local tools directory created: {tool_path}")

        for source in self.config.sources:
            source_path = self.config.workspace.get_path(source.parent)
            if not source_path.exists():
                source_path.mkdir(parents=True)
                _logger.info(f"Source directory created: {source_path}")

        _logger.info("Project initialized")


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
        new_value = (
            input(f"{init_field.metadata['label']} [{current_value}]:") or current_value
        )
        update_dict[init_field.name] = new_value

    return dataclasses.replace(config, **update_dict)
