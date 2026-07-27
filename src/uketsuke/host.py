"""A simple gateway to configured host functions."""

from . import state


def summarize_request(request_file_path):
    return state.configuration["host-functions"]["summarize-request"](
        request_file_path
    )


def dispatch_job(job):
    return state.configuration["host-functions"]["dispatch-job"](job)
