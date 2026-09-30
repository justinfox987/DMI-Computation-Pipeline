# Changelog

Record meaningful delivered changes, newest first. Include a session log or
commit reference when available. Do not use this as a command transcript.

## Unreleased

### Local baseline handoff (2026-09-29)

- Audited the tracked N0-only baseline, recorded its local test result and
  outstanding Step 1 work in [the handoff](docs/sessions/2026-09-29_2024Z-agent-baseline-finalization.md).
- Excluded the two local full VASP distribution copies while leaving the small
  Patch B spec and other untracked patch/source candidates visible for review.
  No VASP assets, production results or Step 1 changes were committed.

### Documentation and coordination

- Prepared repository instructions, status/ownership tracking, a decision log,
  session-log template, evidence guidance and a Windows-friendly setup guide.
- Bundled the current Revision 2.4 LaTeX source and Step 1 implementation spec.
- Preserved the nine supplied older documents under docs/archive with a clear
  notice about superseded frame assumptions.
- Added starter ignore and line-ending rules for local Python/HPC work.

The documentation-and-coordination entries above describe the starter kit, not
Step 1 implementation or a new production validation result.

## Earlier document milestones

- **2026-09-29:** Step 1 implementation specification written.
- **2026-09-26:** Math Revision 2.4 replaced redundant angular bookkeeping with
  vector-based targets, readback, checks and fitting.

Software releases and production validation milestones remain to be recorded
from actual repository commits and evidence.
