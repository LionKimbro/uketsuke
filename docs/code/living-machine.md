```
date: 2026-07-26
```

# uketsuke's Living Machine

uketsuke is a receptionist machine living inside a host program's main
loop.

The host program calls uketsuke to take one turn. uketsuke looks at the
durable situation around it, identifies the most important unfinished
obligation, performs one bounded piece of work, records what happened,
and returns control to the host program.

uketsuke does not own the host program's main loop. It does not decide
when the process starts, when it sleeps, or when it shuts down. It is a
machine that is repeatedly invited to reconcile reality.

## The machine's world

uketsuke lives between two worlds.

The host program supplies the meaning of a request and the operation that
does the work. It provides functions for reading and writing durable
content, discovering available request files, extracting message facts,
executing a job, and characterizing uncertain work.

uketsuke supplies the receptionist behavior: claiming work, preserving
working state, recording outcomes, writing response messages, recovering
from interrupted turns, and deciding when a request is finally done.

The request itself is opaque to uketsuke. uketsuke does not decode the
request to discover its task. It asks the host for the facts it needs, and
the host's `execute_job(job)` function interprets and performs the work.

The machine's durable world is its memory. A process can disappear and
return later; the next turn begins by observing what durable obligations
remain unfinished.

## The central rhythm

The host program repeatedly performs this shape of interaction:

```text
while host_program_is_running:
    result = uketsuke.reconcile_one_turn()
    host_program_responds_to(result)
```

One turn does not attempt to drain the whole system. It performs one
meaningful action, or reports that there is no action to take.

This keeps the machine interruptible and makes its progress visible. A
long backlog becomes a sequence of small reconciliations rather than one
opaque run.

## Priority of attention

Every turn follows the same priority order:

1. Finish unfinished response work.
2. Resolve unfinished or interrupted execution work.
3. Receive and execute one new request from the inbox.
4. Perform maintenance and upkeep.
5. Report that there is no work to do.

This order matters. uketsuke does not begin new work while an earlier
request still has an unresolved response obligation. Durable completion
means both the work and the required answer have been brought to a known
state.

## The living job

When uketsuke claims a request, it creates a current job record. The job
record is the machine's working memory for one request. It is a Python
runtime record, not the request's message format.

Conceptually it contains:

```python
job = {
    "message-id": ...,       # obtained through get_key()
    "inbox-filename": ...,   # original source name
    "claimed-at": ...,       # when uketsuke took responsibility
    "job-file": ...,         # safeguarded current request path
    "state": "claimed",
    "response-address": None,
    "response": None,
    "error": None,
    "characterization": None,
    "attempted-at": None,
    "completed-at": None,
}
```

The record grows as the machine learns what happened. `response` is the
host-produced result when execution succeeds. `error` is a JSON-safe
diagnostic when execution fails. A raw exception object does not become
part of the durable outcome.

The request path in the job record is a safeguarded working reference. It
exists while uketsuke is resolving the request and may be removed after a
terminal outcome record is durable.

## A normal execution

When no response obligation has priority, uketsuke looks for one new
request.

It claims the request and constructs its current job record. Claiming is
the moment responsibility changes: before the claim, the request is new
incoming work; after the claim, uketsuke is responsible for deciding what
happened to it.

uketsuke asks the host's `get_key(request_file, KEY)` function for the
message facts needed by the machine. Typical facts include:

```text
MESSAGE_ID
RESPONSE_ADDRESS
```

The host's `execute_job(job)` function then interprets the request,
selects the task, extracts parameters, and performs the task.

If execution returns normally, the returned value becomes the response
data. uketsuke records a successful outcome and enters the response
reconciliation phase.

If execution raises an ordinary exception, uketsuke catches it at the
execution boundary, records a failed outcome, and enters the response
reconciliation phase. The exception must not escape and destroy the host
program's main loop.

## Interrupted execution

The most difficult state is a request found in uketsuke's working area
without a durable outcome.

This means the host program may have stopped while `execute_job(job)` was
running. uketsuke cannot know from the absence of an outcome whether the
task never began, completed successfully, partially completed, or
completed and failed before the process disappeared.

uketsuke calls:

```python
characterize_job(job)
```

The host must return exactly one of:

```text
retry-safe
do-not-retry
unknown
```

`retry-safe` means uketsuke may attempt `execute_job(job)` again.

`do-not-retry` means the work may have had side effects and must not be
attempted again. uketsuke records an `interrupted` outcome and proceeds to
response reconciliation if a response address is available.

`unknown` means the host cannot recognize or characterize the job. It is
not permission to retry. uketsuke rejects the job without attempting it
again.

This is intentionally a strict contract. The host is the only component
that understands the task's semantics, and uketsuke never guesses that a
second execution is safe.

## Response reconciliation

Execution and response delivery are separate moments in the machine.

The recommended progression is:

```text
execute work
    ↓
durably record outcome
    ↓
reconcile response obligation
    ↓
write and synchronize JSON response
    ↓
record response as sent
    ↓
mark request done
```

The response is a fixed JSON envelope. Its first form is:

```json
{
  "message_id": "...",
  "status": "succeeded",
  "response": {},
  "error": null
}
```

The status is one of:

```text
succeeded   execute_job(job) returned normally
failed      execute_job(job) raised an exception
interrupted work was found in an uncertain in-flight state and was not retried
```

`response` is present when execution returned response data. `error` is
null when no exception or diagnostic applies; otherwise it contains a
JSON-safe string or diagnostic record.

If `RESPONSE_ADDRESS` is `None`, the request does not want a response.
uketsuke records the outcome and completes the request without writing a
response JSON file.

If a response is wanted, uketsuke writes the JSON response through the
host's durable file-writing primitive. The response obligation is not
considered complete until the write has reached the host's promised
durability boundary.

## Why the outcome comes first

uketsuke should durably preserve the execution outcome before attempting
response delivery.

This separates two uncertainties:

```text
What happened when the work ran?
Was the answer successfully delivered?
```

If the process stops after execution but before response delivery, the
next turn sees a response-pending outcome and can continue.

If the process stops after writing the response but before marking the
request done, the next turn sees the existing response evidence and
finishes the completion transition without executing the task again.

This is why the machine reconciles durable obligations instead of merely
running a forward sequence of functions.

## Completion

A request becomes done only when its terminal outcome is durably recorded
and its response obligation is resolved:

```text
successful work + response sent       → done / succeeded
failed work + failure response sent   → done / failed
interrupted work + response sent      → done / interrupted
rejected work                         → done / rejected
no response requested                  → done / corresponding status
```

The request's safeguarded working copy may then be removed. The compact
terminal outcome record remains as the machine's durable explanation of
what happened.

## Maintenance

Maintenance is deliberately last in the attention order. It may clean
temporary artifacts, truncate operational logs, reconcile stale records,
or perform other bounded upkeep.

Maintenance must not erase evidence that is still needed to resolve a
request. Retention and deduplication policies are future extensions until
the initial lifecycle is stable.

## Core invariants

The living machine should preserve these truths:

- A request is either still incoming, under uketsuke's responsibility, or
  represented by a terminal outcome.
- A task is not executed again merely because response delivery was
  interrupted.
- Uncertain work is never retried unless `characterize_job(job)` returns
  `retry-safe`.
- `unknown` characterization produces rejection, not execution.
- A response is JSON and is written only when a response address exists.
- A task exception becomes a failure outcome rather than escaping through
  the host-program loop.
- Response reconciliation has priority over new execution.
- The host program owns task meaning; uketsuke owns lifecycle meaning.

uketsuke is therefore a small durable receptionist: it continually looks
for the most important unresolved fact about its world, performs the next
safe action, records the result, and waits for the host program to invite
the next turn.
