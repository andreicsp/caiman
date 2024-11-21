"""
Filesystem operations to be run on the remote device.
Compatible micropython code
"""
import os


def resolve_path(relative_path):
    """
    Resolve a relative path to an absolute path.
    """
    if relative_path.startswith("/"):
        return relative_path
    # Get the current working directory
    cwd = os.getcwd()
    # Split the working directory and the relative path into components
    path_parts = cwd.split("/") + relative_path.split("/")

    # Resolve '.' and '..' manually
    resolved_parts = []
    for part in path_parts:
        if part == "." or part == "":
            continue
        elif part == "..":
            if resolved_parts:
                resolved_parts.pop()
        else:
            resolved_parts.append(part)

    # Join the resolved parts to form the absolute path
    absolute_path = "/" + "/".join(resolved_parts)
    return absolute_path


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
        path = resolve_path(path)
        if path.startswith(cwd) or cwd.startswith(path):
            continue
        os.remove(path)
        files.append(path)

    return files
