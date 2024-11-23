"""
Base classes for defining plugins and goals.
"""
import dataclasses
import logging
import sys
from abc import ABC, abstractmethod
from typing import Tuple, Type

from caiman.config import Command, Config


class Goal(ABC):
    """
    A goal is a specific task that can be executed by a plugin.
    """
    def __init__(self, config: Config):
        """
        Initialize the goal with the given project configuration.
        :param config: The project configuration
        """
        self.config = config
        self._logger = logging.getLogger(self.name)

    @property
    @abstractmethod
    def help(self):
        """
        Return the help message for the goal.
        """

    @property
    @abstractmethod
    def name(self):
        """
        Return the name of the goal for the command line interface.
        """
        return self.__class__.__name__

    @abstractmethod
    def get_schema(self) -> Type:
        """
        Return the schema for the command parameters.
        """

    @abstractmethod
    def __call__(self, command: Command):
        """
        Execute the goal with the given command.
        """

    def fail(self, message):
        """
        Exit the program with an error message.
        """
        fail(f"[{self.name}] {message}")

    def info(self, message):
        """
        Log an informational message
        """
        self._logger.info(f"{message}")


class Plugin(ABC):
    """
    A plugin is a collection of goals that can be executed by the build tool.
    """
    def __init__(self, config: Config):
        """
        Initialize the plugin with the given project configuration.
        :param config: The project configuration
        """
        self.config = config

    @abstractmethod
    def get_goals(self) -> Tuple[Goal]:
        """
        Return the goals provided by the plugin.
        """

    @property
    def name(self):
        """
        Return the name of the plugin.
        """
        return self.__class__.__name__


class PluginProvider(ABC):
    """
    A plugin provider is a factory for creating plugins.
    """
    @abstractmethod
    def get_plugins(self, config: Config):
        return ()


def fail(message):
    """
    Exit the program with an error message.
    """
    print(message)
    sys.exit(1)


def param(
    help, default=dataclasses.MISSING, default_factory=dataclasses.MISSING, **kwargs
):
    """
    A dataclass field with help text indexed by the command line parser.
    """
    return dataclasses.field(
        metadata={"help": help},
        default=default,
        default_factory=default_factory,
        **kwargs
    )
