"""
Plugin loader for caiman
"""

from typing import List
from caiman.config import Config
from importlib import import_module

from caiman.plugins.base import Plugin, PluginProvider
from caiman.plugins.workspace import WorkspacePlugin
from caiman.plugins.core import CorePluginProvider


def get_pre_init_plugins(config) -> List[Plugin]:
    """
    Get plugins that should run before the config is loaded
    """
    return [WorkspacePlugin(config)]


def load_plugins(config: Config) -> List[Plugin]:
    """
    Load plugins from a list of class references
    """
    plugins = []
    class_refs = config.workspace.plugins
    if not class_refs:
        class_refs = [f"{CorePluginProvider.__module__}.{CorePluginProvider.__name__}"]

    for class_ref in class_refs:
        module_name, class_name = class_ref.rsplit(".", 1)
        module = import_module(module_name)
        class_obj = getattr(module, class_name)
        if issubclass(class_obj, PluginProvider):
            plugins.extend(class_obj().get_plugins(config))
        elif issubclass(class_obj, Plugin):
            plugin = class_obj(config=config)
            plugins.append(plugin)
        else:
            raise TypeError(f"{class_obj} is not a subclass of Plugin or PluginProvider")

    return plugins

