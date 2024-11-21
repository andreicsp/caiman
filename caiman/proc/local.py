import subprocess
import sys

from caiman.proc.base import (
    CommandError,
    MicroPythonProcess,
    find_micropython_path,
    follow_subprocess,
)


class LocalMicroPythonProcess(MicroPythonProcess):
    def __init__(self, executable=None):
        self.executable = executable or find_micropython_path()

    def mip_install(self, index: str, target: str, packages: dict, no_mpy):
        code = ["import mip"]
        for name, version in packages.items():
            code.append(
                f"mip.install('{name}', version='{version}', index='{index}', target='{target}',mpy={not no_mpy})"
            )
        return self.run_code(code, follow=False)

    def run_code(self, code, cwd=None, follow=False):
        # Run the given lines of MicroPython code
        cmd = [self.executable, "-c", ";".join(code)]
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
