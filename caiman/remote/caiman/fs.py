"""
Filesystem operations to be run on the remote device.
Compatible micropython code
"""
import os


def iwalk(parent):
    """
    Recursively walk the filesystem starting from the parent directory.
    Yields files starting from the innermost directory.
    Folders are yielded after the files they contain to allow for easier deletion.
    """
    stack = [parent]
    visited = set()
    while stack:
        current = stack[-1]
        if current in visited:
            yield current
            stack.pop()
            continue

        try:
            os.stat(current)
        except OSError:
            stack.pop()
            continue

        for entry in os.ilistdir(current):
            name, etype = entry[0], entry[1]
            is_dir = etype == 0x4000

            path = f"{current.rstrip('/')}/{name}"
            if is_dir:
                stack.append(path)
            else:
                yield path

        visited.add(current)


def walk(parent):
    return list(iwalk(parent))


def rmtree(parent):
    """
    Recursively delete the directory and all its contents.
    """
    files = []
    cwd = os.getcwd()
    for path in iwalk(parent):
        if path.startswith(cwd) or cwd.startswith(path):
            continue
        os.remove(path)
        files.append(path)

    return files
