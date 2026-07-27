"""The active-job record machine."""

from datetime import datetime, timezone
import traceback

from . import fsio, paths


g = {
    "job": None,
}


def read_the_current_active_job_if_there_is_one():
    g["job"] = fsio.read_file(paths.path("job"), ["json"])


def create_new(info):
    g["job"] = {
        "request-file-path": info["request-file-path"],
        "request-original-filename": info["request-original-filename"],
        "status": info["status"],
        "completion-status": info["completion-status"],
        "request-id": info["request-id"],
        "error": info["error"],
        "history": [info["history-entry"]],
    }
    if "reply-to" in info:
        g["job"]["reply-to"] = info["reply-to"]

    durably_replace_the_current_job_with_its_new_state()


def durably_replace_the_current_job_with_its_new_state():
    fsio.write_file(paths.path("job-nextstate"), g["job"], ["json"])
    fsio.copy_file(paths.path("job-nextstate"), paths.path("job"))
    fsio.delete_file(paths.path("job-nextstate"))


def append_result(operation, result, flags):
    _check_append_result_flags(flags)

    error = None
    if "error" in flags:
        error = traceback.format_exc()
        g["job"]["error"] = error

    history_entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "operation": operation,
        "result": result,
        "error": error,
    }
    g["job"]["history"].append(history_entry)
    durably_replace_the_current_job_with_its_new_state()


def _check_append_result_flags(flags):
    unexpected = set(flags) - {"error"}
    if unexpected:
        raise ValueError(f"Unexpected flags: {unexpected}")
