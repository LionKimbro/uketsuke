"""The one-turn receptionist machine."""

from datetime import datetime, timezone
import traceback

from . import fsio, host, jobs, paths


g = {
    "operation": None,
    "quit": False,
}


panel = {
    "turn-count": 0,
    "last-operation": None,
    "last-result": None,
    "last-error": None,
    "quit": False,
}


def do_tick():
    if g["quit"]:
        return False

    panel["turn-count"] += 1
    clear_the_observation_facts_for_this_new_turn()

    g["operation"] = identify_what_needs_to_be_done()

    perform_the_selected_operation()
    panel["last-operation"] = g["operation"]

    return not g["quit"]


def clear_the_observation_facts_for_this_new_turn():
    panel["last-operation"] = None
    panel["last-result"] = None
    panel["last-error"] = None


def identify_what_needs_to_be_done():
    jobs.read_the_current_active_job_if_there_is_one()

    if jobs.g["job"] is not None:
        if jobs.g["job"]["status"] == "dead-letter-pending":
            return "complete-dead-letter-transition"

        if jobs.g["job"]["status"] == "claimed":
            return "execute-claimed-job"

        if jobs.g["job"]["status"] == "executed":
            return "send-job-reply"

        return "idle"

    if fsio.list_files(paths.path("inbox")):
        return "claim-inbox-request"

    return "idle"


def perform_the_selected_operation():
    if g["operation"] == "idle":
        return

    if g["operation"] == "complete-dead-letter-transition":
        perform_operation_completing_the_dead_letter_transition()
        return

    if g["operation"] == "execute-claimed-job":
        perform_operation_executing_the_claimed_job()
        return

    if g["operation"] == "send-job-reply":
        perform_operation_sending_the_job_reply()
        return

    if g["operation"] == "claim-inbox-request":
        perform_operation_claiming_an_inbox_request()
        return

    raise ValueError(f"Unsupported runtime operation: {g['operation']}")


def perform_operation_claiming_an_inbox_request():
    inbox_files = fsio.list_files(paths.path("inbox"))
    selected_request = max(inbox_files, key=lambda file: file["last-modified"])
    selected_request_path = selected_request["path"]

    fsio.copy_file(selected_request_path, paths.path("opaque-request-file"))

    try:
        request_id = host.summarize_request(paths.path("opaque-request-file"))
    except Exception:
        error = traceback.format_exc()
        jobs.create_new(
            {
                "request-file-path": str(paths.path("opaque-request-file")),
                "request-original-filename": selected_request_path.name,
                "request-id": None,
                "status": "dead-letter-pending",
                "completion-status": "dead-letter",
                "error": error,
                "history-entry": make_history_entry(
                    "summarize-request", "failed", error
                ),
            }
        )
        panel["last-result"] = "created-dead-letter-pending-job"
        panel["last-error"] = error
    else:
        info = {
            "request-file-path": str(paths.path("opaque-request-file")),
            "request-original-filename": selected_request_path.name,
            "request-id": request_id,
            "status": "claimed",
            "completion-status": None,
            "error": None,
            "history-entry": make_history_entry(
                "summarize-request", "succeeded", None
            ),
        }
        jobs.create_new(info)
        panel["last-result"] = "created-claimed-job"

    fsio.delete_file(selected_request_path)


def perform_operation_executing_the_claimed_job():
    job = jobs.g["job"]
    job["status"] = "execution-attempted"
    jobs.append_result("prepare-dispatch", "execution-attempted", [])

    try:
        response = host.dispatch_job(job)
    except Exception:
        job["completion-status"] = "fail"
        job["status"] = "executed"

        jobs.append_result("dispatch-job", "failed", ["error"])
        panel["last-result"] = "dispatch-failed"
        panel["last-error"] = job["error"]
        return

    job["response"] = response
    job["completion-status"] = "success"
    job["status"] = "executed"

    jobs.append_result("dispatch-job", "succeeded", [])
    panel["last-result"] = "dispatch-succeeded"


def perform_operation_sending_the_job_reply():
    job = jobs.g["job"]

    try:
        host.send_reply(job)
    except Exception:
        jobs.append_result("send-job-reply", "failed", ["error"])
        panel["last-result"] = "reply-failed"
        panel["last-error"] = job["error"]
        return

    job["status"] = "reported"
    jobs.append_result("send-job-reply", "succeeded", [])
    panel["last-result"] = "reply-succeeded"


def perform_operation_completing_the_dead_letter_transition():
    job = jobs.g["job"]
    timestamp = failed_summary_timestamp_from(job)
    dead_letter_directory = paths.path("dead-letter")
    dead_letter_job = dead_letter_directory / f"job-{timestamp}.json"
    dead_letter_request = (
        dead_letter_directory / f"job-{timestamp}-original-request"
    )
    opaque_request = paths.path("opaque-request-file")

    if fsio.read_file(opaque_request, ["bytes"]) is not None:
        fsio.copy_file(opaque_request, dead_letter_request)

    job["status"] = "transferred-to-dead-letter-directory"
    job["history"].append(
        make_history_entry("transfer-to-dead-letter", "completed", None)
    )
    fsio.write_file(dead_letter_job, job, ["json"])

    if fsio.read_file(opaque_request, ["bytes"]) is not None:
        fsio.delete_file(opaque_request)

    fsio.delete_file(paths.path("job"))
    jobs.g["job"] = None
    panel["last-result"] = "completed-dead-letter-transition"


def failed_summary_timestamp_from(job):
    for history_entry in job["history"]:
        if history_entry["operation"] == "summarize-request":
            timestamp = datetime.fromisoformat(history_entry["timestamp"])
            timestamp = timestamp.astimezone(timezone.utc)
            return timestamp.strftime("%Y%m%dT%H%M%S%fZ")

    raise ValueError("Dead-letter job has no summarize-request history entry")


def make_history_entry(operation, result, error):
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "operation": operation,
        "result": result,
        "error": error,
    }


def transition_to_the_quit_state():
    g["quit"] = True
    panel["quit"] = True
