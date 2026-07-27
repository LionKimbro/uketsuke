"""Configured and derived paths for the uketsuke program."""

from . import fsio, state


paths = {
    "working": None,
    "done": None,
    "job": None,
    "job-nextstate": None,
}


def ensure_that_the_necessary_directories_exist_when_the_program_starts_up():
    inbox = state.configuration["directories"]["inbox"]
    work_space = state.configuration["directories"]["work-space"]

    fsio.mkdir_and_sync(inbox)
    fsio.mkdir_and_sync(work_space)

    paths["working"] = work_space / "working"
    paths["done"] = work_space / "done"
    paths["job"] = paths["working"] / "job.json"
    paths["job-nextstate"] = paths["working"] / "job-nextstate.json"

    fsio.mkdir_and_sync(paths["working"])
    fsio.mkdir_and_sync(paths["done"])


def path(name):
    if name in {"inbox", "work-space"}:
        return state.configuration["directories"][name]

    if name in {"working", "done", "job", "job-nextstate"}:
        return paths[name]

    raise ValueError(f"Unsupported path name: {name}")
