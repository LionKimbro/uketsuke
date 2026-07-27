"""Startup initialization and repair for one interrupted job transition."""

import json

from . import fsio, jobs, paths, state


def initialize_program_at_startup_time_once(new_configuration):
    state.initialize_configuration_when_the_program_starts_up(new_configuration)
    paths.ensure_that_the_necessary_directories_exist_when_the_program_starts_up()
    repair_system_from_potentially_crashed_state()


def repair_system_from_potentially_crashed_state():
    heal_incomplete_job_transition()
    jobs.read_the_current_active_job_if_there_is_one()

    if jobs.g["job"] is None:
        return

    remove_the_inbox_duplicate_of_a_claimed_job()
    heal_interrupted_execution_job()


def heal_incomplete_job_transition():
    authoritative_job_file = paths.path("job")
    staged_replacement_job_file = paths.path("job-nextstate")

    try:
        staged_job = fsio.read_file(staged_replacement_job_file, ["json"])
    except (json.JSONDecodeError, UnicodeDecodeError):
        fsio.delete_file(staged_replacement_job_file)
        return

    if staged_job is None:
        return

    fsio.copy_file(
        staged_replacement_job_file,
        authoritative_job_file,
    )
    fsio.delete_file(staged_replacement_job_file)


def heal_interrupted_execution_job():
    if jobs.g["job"]["status"] != "execution-attempted":
        return

    jobs.g["job"]["status"] = "claimed"
    jobs.append_result(
        "startup-repaired-interrupted-execution",
        "reset-to-claimed-for-reexecution",
        [],
    )


def remove_the_inbox_duplicate_of_a_claimed_job():
    original_filename = jobs.g["job"]["request-original-filename"]

    for file_description in fsio.list_files(paths.path("inbox")):
        if file_description["path"].name == original_filename:
            fsio.delete_file(file_description["path"])
            return
