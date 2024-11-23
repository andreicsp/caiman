from dataclasses import dataclass

from caiman.config import Command
from caiman.plugins.base import Goal, Plugin, param
from caiman.proc.device import DeviceMicroPythonProcess


@dataclass
class RunnerCommand:
    target: str = param("Python module to run on the device")


class RunnerGoal(Goal):
    def __init__(self, device: DeviceMicroPythonProcess):
        self._device = device

    @property
    def help(self):
        return "Run a Python module on the device"

    @property
    def name(self):
        return "run"

    def get_schema(self):
        return RunnerCommand

    def __call__(self, command: Command):
        command = RunnerCommand(**command.params)
        return self._device.run_main(command.target)


class RunnerPlugin(Plugin):
    def __init__(self, config):
        super().__init__(config)
        self._device = DeviceMicroPythonProcess(config=config.device)

    def get_goals(self):
        return (RunnerGoal(device=self._device),)
