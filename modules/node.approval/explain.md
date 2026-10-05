# Human approval

## What
Pauses the run and shows an approval card in the chat UI. The run resumes exactly where it stopped, even after a restart if memory is persistent.

## Why
Some actions (refunds, emails, publishing) should never happen without a person agreeing. The run pauses safely and resumes exactly where it stopped.

## Trade-off
Someone has to be available to approve; long waits leave users waiting too.
