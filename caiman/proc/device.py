import importlib
import json
import logging
import subprocess
import sys
from pathlib import Path
from typing import Callable

from caiman.config import Device
from caiman.proc.base import CommandError, MicroPythonProcess, follow_subprocess

_logger = logging.getLogger("device")


class DeviceMicroPythonProcess(MicroPythonProcess):
    def __init__(self, config: Device, mount_path: str = None):
        self.config = config
        self.mount_path = mount_path

    def mip_install(self, index: str, target: str, packages: dict, no_mpy):
        command = ["mip"]
        command += ["--no-mpy"] if no_mpy else []
        command += ["--index", self.index, "--target", str(target), "install"] + [
            "@".join(package) for package in self.packages
        ]
        return self.run_mp_remote_cmd(*command)

    def run_mp_remote_cmd(self, *args, cwd=None, follow=False):
        # Start a subprocess of the same Python interpreter
        cmd = [sys.executable, "-m", "mpremote"]
        if self.config.port:
            cmd.extend(["connect", self.config.port])

        if self.mount_path:
            cmd.extend(["mount", "-l", str(self.mount_path), "+"])

        cmd.extend(list(args))
        cmd.extend(["+", "disconnect"])
        _logger.debug(f"Running command: {' '.join(cmd)}")
        proc = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=cwd
        )
        if follow:
            follow_subprocess(proc)
            sys.exit(proc.returncode)

        out, err = proc.communicate()
        if proc.returncode != 0:
            raise CommandError(cmd[-1], stdout=out, stderr=err)

        return out

    def run_code(self, code, follow=False):
        if isinstance(code, list):
            code = ";".join(code)
        args = ["soft-reset"]
        if self.mount_path:
            args.extend(["mount", "-l", str(self.mount_path), "+"])

        args.extend(["exec", code])
        return self.run_mp_remote_cmd(*args, follow=follow)

    def run_vfs_python_func(self, func: Callable, **kwargs):
        kwarg_json = json.dumps(kwargs)
        kwarg_decode = f"json.loads('{kwarg_json}')"
        func_module = importlib.import_module(func.__module__)
        if not func_module or not func_module.__file__:
            raise ImportError(f"Could not import module {func.__module__}")

        import_mod = func.__module__.split(".", 2)[-1]
        mount_path = Path(func_module.__file__).parent.parent
        func_name = func.__name__

        code = []
        code.append(f"from {import_mod} import {func_name}")
        code.append("import json")
        code.append(f"print(':::' + json.dumps({func_name}(**{kwarg_decode})))")

        output = (
            DeviceMicroPythonProcess(config=self.config, mount_path=str(mount_path))
            .run_code(code)
            .decode()
        )
        lines = output.splitlines()
        lines = [line[3:] for line in lines if line.startswith(":::")]
        output = lines[-1]
        result = json.loads(output)
        return result
