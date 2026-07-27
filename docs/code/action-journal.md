# Action Journal Mechanism

uketsuke needs an action-journal mechanism for recording the execution
boundary of work.

The mechanism must preserve the fact that an action is about to run, or
that the action has run, so that a later uketsuke turn can distinguish
between work that has never been attempted and work that may have been
interrupted after an attempt began.

This is part of uketsuke's dependable execution model. It is not merely a
performance optimization and it is not the same thing as the in-memory
action hint.

The mechanism's implementation is intentionally unspecified here. This
document does not prescribe its storage format, record shape, file layout,
write protocol, or reconciliation algorithm.

The mechanism must support the conceptual distinction between:

- an action that has not been attempted;
- an action that is about to run or has begun running;
- an action that has run and has a known outcome.

The resulting information is used when uketsuke encounters work whose
execution history is uncertain. It supports the host-program's
`characterize_job(job)` decision about whether an action is safe to retry,
must not be retried, or cannot be recognized.
