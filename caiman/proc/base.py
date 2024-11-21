import select
import shutil
import sys
from abc import ABC, abstractmethod


class CommandError(Exception):
    def __init__(self, command, stdout, stderr):
        self.command = command
        self.stdout = stdout
        self.stderr = stderr

    def __str__(self):
        output = [f"command:\n{self.command}"]
        if self.stdout:
            output.append(f"stdout:\n{self.stdout.decode()}")
        if self.stderr:
            output.append(f"stderr:\n{self.stderr.decode()}")
        return "\n".join(output)


class MicroPythonProcess(ABC):
    @abstractmethod
    def mip_install(self, index: str, target: str, packages: dict, no_mpy):
        pass

    def run_main(self, module_name):
        return self.run_code(f"import {module_name};", follow=True)

    @abstractmethod
    def run_code(self, code, follow=False):
        pass


def follow_subprocess(proc):
    while True:
        reads = [proc.stdout.fileno(), proc.stderr.fileno()]
        ret = select.select(reads, [], [])

        for fd in ret[0]:
            if fd == proc.stdout.fileno():
                output = proc.stdout.readline()
                if output:
                    output = output.decode() if isinstance(output, bytes) else output
                    sys.stdout.write(output)
                    sys.stdout.flush()
            if fd == proc.stderr.fileno():
                error = proc.stderr.readline()
                if error:
                    error = error.decode() if isinstance(error, bytes) else error
                    sys.stderr.write(error)
                    sys.stderr.flush()

        if proc.poll() is not None:
            break


def find_micropython_path():
    # Find the MicroPython binary on the system path
    micropython_path = shutil.which("micropython")
    if micropython_path:
        return micropython_path
    else:
        raise FileNotFoundError("MicroPython binary not found in system PATH")
