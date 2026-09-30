# Changelog

Record meaningful delivered changes, newest first. Include a session log or
commit reference when available. Do not use this as a command transcript.

## Unreleased

### Step 1 original-file reader repair handoff (2026-09-30)

- Committed the reviewed reader repair for repeated OSZICAR sphere tables, SDA/CGA iterations, actual OUTCAR run banners and `Iteration I(E)` association, with distinct missing-summary and missing-OUTCAR-footer checks. The original Fe sample parses at ionic/electronic step 1/50 (95 sphere tables, one ionic summary); 17 focused and 52 total local software tests pass. No push.
- The sample's requested both-Fe +x directions do not establish physical F0 realization, and zero lambda/field cannot verify a nonzero-lambda convention. No versioned config/reference-bound read, production gate or VASP job; see [real-sample handoff](docs/sessions/2026-09-30_1610Z-agent-step1-reader-real-sample.md).

### Step 1 final review follow-up (2026-09-30)

- Rejected malformed or broadcastable QSPIRAL values at stored/requested/run/echo boundaries and mismatched per-species RWIGS between otherwise valid partners.
- Kept zero-field states valid without claiming factor-two evidence below printed resolution; retained separate zero-field consistency and positive-signal Fe excerpt checks. See [final review log](docs/sessions/2026-09-30_0024Z-agent-step1-final-review.md). No production VASP validation.

### Step 1 corrective review (2026-09-30)

- Bound readback and row gates to checked config/run file hashes and re-read sphere
  moments, checked stored q/target identity, and added safe CLI wrapped-partner
  representation without changing physical targets.
- Allowed one common-z pair-validation rotation while retaining raw model spins;
  checked printed penalty and signed field against MW_int within decimal rounding;
  required indexed terminal OSZICAR and final OUTCAR loop agreement or failed closed.
  Synthetic tests are not VASP validation. See [corrective session log](docs/sessions/2026-09-30_0005Z-agent-step1-review-fixes.md).

### Step 1 offline vector software path (2026-09-29)

- Added versioned lab-frame target recipes and INCAR fragments, strict OSZICAR
  sphere-moment readback with separate electronic convergence, signed realization
  checks, one canonical cell-translation bond kernel and two-sided diagnostic rows.
- Added offline CLI input/readback/row/weighted-solve entry points and synthetic
  regression coverage while preserving the historical N0 manifest and trace.
  Missing BFO symmetry basis, production trace/parity and noise evidence are
  explicit blockers, not new validation passes. See [local usage](docs/STEP1_LOCAL_USAGE.md)
  and the [implementation handoff](docs/sessions/2026-09-29_2328Z-agent-dmi-step1-vectors.md).

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
