"""Configured and derived paths for the uketsuke program."""

from . import fsio, state


paths = {
    "working": None,
    "done": None,
    "dead-letter": None,
    "job": None,
    "job-nextstate": None,
    "opaque-request-file": None,
}


def ensure_that_the_necessary_directories_exist_when_the_program_starts_up():
    inbox = state.configuration["directories"]["inbox"]
    work_space = state.configuration["directories"]["work-space"]

    fsio.mkdir_and_sync(inbox)
    fsio.mkdir_and_sync(work_space)

    paths["working"] = work_space / "working"
    paths["done"] = work_space / "done"
    paths["dead-letter"] = work_space / "dead-letter"
    paths["job"] = paths["working"] / "job.json"
    paths["job-nextstate"] = paths["working"] / "job-nextstate.json"
    paths["opaque-request-file"] = paths["working"] / "opaque-request-file"

    fsio.mkdir_and_sync(paths["working"])
    fsio.mkdir_and_sync(paths["done"])
    fsio.mkdir_and_sync(paths["dead-letter"])


def path(name):
    if name in state.configuration["directories"]:
        return state.configuration["directories"][name]

    if name in paths:
        return paths[name]

    raise ValueError(f"Unsupported path name: {name}")
