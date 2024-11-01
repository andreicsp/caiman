import dataclasses
import logging
import sys
from abc import ABC, abstractmethod
from typing import Tuple, Type

from caiman.config import Command, Config


class Goal(ABC):
    def __init__(self, config: Config):
        self.config = config
        self._logger = logging.getLogger(self.name)

    @property
    @abstractmethod
    def help(self):
        pass

    @property
    @abstractmethod
    def name(self):
        return self.__class__.__name__

    @abstractmethod
    def get_schema(self) -> Type:
        return

    @abstractmethod
    def __call__(self, command: Command):
        pass

    def fail(self, message):
        fail(f"[{self.name}] {message}")

    def info(self, message):
        self._logger.info(f"{message}")


class Plugin(ABC):
    def __init__(self, config: Config):
        self.config = config

    @abstractmethod
    def get_goals(self) -> Tuple[Goal]:
        return ()

    @property
    def name(self):
        return self.__class__.__name__


class PluginProvider(ABC):
    @abstractmethod
    def get_plugins(self, config: Config):
        return ()


def fail(message):
    print(message)
    sys.exit(1)


def param(
    help, default=dataclasses.MISSING, default_factory=dataclasses.MISSING, **kwargs
):
    return dataclasses.field(
        metadata={"help": help},
        default=default,
        default_factory=default_factory,
        **kwargs,
    )
