"""A small JSON-file host environment for uketsuke development."""

import json
import os
from pathlib import Path


def make_configuration(inbox, work_space):
    return {
        "host-os-functionality": {
            "read-file": read_file,
            "write-and-sync": write_and_sync,
            "copy-and-sync": copy_and_sync,
            "delete-and-sync": delete_and_sync,
            "mkdir-and-sync": mkdir_and_sync,
            "list-files": list_files,
        },
        "host-functions": {
            "summarize-request": summarize_request,
            "dispatch-job": dispatch_job,
        },
        "directories": {
            "inbox": Path(inbox),
            "work-space": Path(work_space),
        },
    }


def read_file(src):
    return Path(src).read_bytes()


def write_and_sync(destination, content):
    with Path(destination).open("wb") as f:
        f.write(content)
        f.flush()
        os.fsync(f.fileno())


def copy_and_sync(src, destination):
    content = read_file(src)
    write_and_sync(destination, content)


def delete_and_sync(path):
    path = Path(path)
    path.unlink()
    sync_directory(path.parent)


def mkdir_and_sync(path):
    path = Path(path)
    if path.exists():
        return

    path.mkdir()
    sync_directory(path.parent)


def list_files(path):
    return sorted(
        (child for child in Path(path).iterdir() if child.is_file()),
        key=lambda child: child.name,
    )


def sync_directory(directory):
    if os.name == "nt":
        return

    descriptor = os.open(directory, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def summarize_request(request_file_path):
    try:
        request = json.loads(read_file(request_file_path))
    except json.JSONDecodeError as error:
        raise ValueError("The request file does not contain valid JSON") from error

    if not isinstance(request, dict):
        raise ValueError("The request JSON must be an object")

    if "request-id" not in request:
        raise ValueError("The request JSON does not contain request-id")

    summary = {"request-id": request["request-id"]}
    if request.get("reply-to") is not None:
        summary["reply-to"] = request["reply-to"]

    return summary


def dispatch_job(job):
    request = json.loads(read_file(job["request-file-path"]))

    print("I received this job to execute:")
    print(json.dumps(job, indent=2, default=str))
    print("This is the contents of the job request:")
    print(json.dumps(request, indent=2))

    return None
