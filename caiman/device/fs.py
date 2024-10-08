from pathlib import Path
from caiman.device.handler import DeviceHandler, CommandError
from caiman.mount import fs
import json


class FileSystem:
    def __init__(self, device: DeviceHandler):
        self.device = device

    def walk(self, path):
        return self.device.run_vfs_python_func(fs.walk, parent=path)

    def rmtree(self, path):
        return self.device.run_vfs_python_func(fs.rmtree, parent=path)

    def upload(self, src, dst, cwd=None):
        cmd = ['fs', 'cp']
        full_src = Path(src) if cwd is None else Path(cwd) / src
        if full_src.is_dir():
            cmd.append('-r')

        dst = dst.strip('/')
        dst = f":{dst}"
        cmd.extend([src, dst])
        return self.device.run_mp_remote_cmd(*cmd, cwd=cwd)

    def mkdir(self, path):
        parts = path.split('/')
        for i in range(1, len(parts)):
            subpath = '/'.join(parts[:i + 1])
            try:
                self.device.run_mp_remote_cmd('mkdir', subpath)
                print(f'Created {subpath}')
            except CommandError:
                pass

    def get_file_contents(self, file_path):
        return self.device.run_mp_remote_cmd('cat', file_path)

    def get_json(self, file_path, ignore_missing=False):
        try:
            contents = self.get_file_contents(file_path)
        except CommandError as e:
            if ignore_missing:
                contents = '{}'
            else:
                raise e
        return json.loads(contents)
