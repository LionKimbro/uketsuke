"""The codec and durability gateway."""

import json

from . import state


def _check_flags(flags):
    flag_set = set(flags)
    representations = {"bytes", "text", "json"}

    if not flag_set & representations:
        raise ValueError("One representation flag is required")

    if len(flag_set & representations) > 1:
        raise ValueError("Only one representation flag is allowed")

    unexpected = flag_set - representations - {"required"}
    if unexpected:
        raise ValueError(f"Unexpected flags: {unexpected}")


def read_file(src, flags):
    _check_flags(flags)

    fn = state.configuration["host-os-functionality"]["read-file"]
    try:
        value = fn(src)
    except FileNotFoundError:
        if "required" in flags:
            raise
        return None

    if "json" in flags:
        return json.loads(value)

    if "text" in flags:
        return value.decode("utf-8")

    if "bytes" in flags:
        return value

    raise ValueError("A representation flag is required")


def write_file(destination, value, flags):
    _check_flags(flags)

    if "bytes" in flags:
        content = value

    if "text" in flags:
        content = value.encode("utf-8")

    if "json" in flags:
        content = json.dumps(value).encode("utf-8")

    fn = state.configuration["host-os-functionality"]["write-and-sync"]
    fn(destination, content)


def copy_file(src, destination):
    fn = state.configuration["host-os-functionality"]["copy-and-sync"]
    fn(src, destination)


def delete_file(path):
    fn = state.configuration["host-os-functionality"]["delete-and-sync"]
    fn(path)


def mkdir_and_sync(path):
    fn = state.configuration["host-os-functionality"]["mkdir-and-sync"]
    fn(path)


def list_files(path):
    fn = state.configuration["host-os-functionality"]["list-files"]
    return fn(path)
