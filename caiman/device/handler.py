import importlib
import json
import logging
import select
import subprocess
import sys
from pathlib import Path
from typing import Callable, Optional

from caiman.config import Config

_logger = logging.getLogger("device")


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


class DeviceHandler:
    def __init__(self, config: Optional[Config] = None):
        self.config = config or Config.load()

    def _follow_subprocess(self, proc):
        while True:
            reads = [proc.stdout.fileno(), proc.stderr.fileno()]
            ret = select.select(reads, [], [])

            for fd in ret[0]:
                if fd == proc.stdout.fileno():
                    output = proc.stdout.readline()
                    if output:
                        output = (
                            output.decode() if isinstance(output, bytes) else output
                        )
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

    def run_mp_remote_cmd(self, *args, mount_path=None, cwd=None, follow=False):
        # Start a subprocess of the same Python interpreter
        cmd = [sys.executable, "-m", "mpremote"]
        if self.config.device.port:
            cmd.extend(["connect", self.config.device.port])

        if mount_path:
            cmd.extend(["mount", "-l", str(mount_path), "+"])

        cmd.extend(list(args))
        cmd.extend(["+", "disconnect"])
        _logger.info(f"Running command: {' '.join(cmd)}")
        proc = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=cwd
        )
        if follow:
            self._follow_subprocess(proc)
            sys.exit(proc.returncode)

        out, err = proc.communicate()
        if proc.returncode != 0:
            raise CommandError(cmd[-1], stdout=out, stderr=err)

        return out

    def run_main(self, module_name):
        return self.run_python_code(f"import {module_name};", follow=True)

    def run_python_code(self, code, mount_path=None, reset=True, follow=False):
        if isinstance(code, list):
            code = ";".join(code)
        args = []
        if reset:
            args.append("soft-reset")
        if mount_path:
            args.extend(["mount", "-l", str(mount_path), "+"])

        args.extend(["exec", code])
        return self.run_mp_remote_cmd(*args, mount_path=mount_path, follow=follow)

    def run_vfs_python_func(self, func: Callable, **kwargs):
        kwarg_json = json.dumps(kwargs)
        kwarg_decode = f"json.loads('{kwarg_json}')"
        func_module = importlib.import_module(func.__module__)
        if not func_module or not func_module.__file__:
            raise ImportError(f"Could not import module {func.__module__}")

        import_mod = func.__module__.rsplit(".", 1)[1]
        mount_path = Path(func_module.__file__).parent
        func_name = func.__name__

        code = []
        code.append(f"from {import_mod} import {func_name}")
        code.append("import json")
        code.append(f"print(':::' + json.dumps({func_name}(**{kwarg_decode})))")

        output = self.run_python_code(code, mount_path=mount_path).decode()
        lines = output.splitlines()
        lines = [line[3:] for line in lines if line.startswith(":::")]
        output = lines[-1]
        result = json.loads(output)
        return result
