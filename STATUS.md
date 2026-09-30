# Current project status

**Last reconciled:** 2026-09-30 UTC on the local Step 1 branch; corrective review [session log](docs/sessions/2026-09-30_0005Z-agent-step1-review-fixes.md) follows the [implementation log](docs/sessions/2026-09-29_2328Z-agent-dmi-step1-vectors.md). Baseline [handoff finalization](docs/sessions/2026-09-29_2024Z-agent-baseline-finalization.md) remains local.

**Code checkout inspected:** tracked `pipeline v3/` package, tests, N0 evidence and manifest; no production VASP revalidation.

**Integration branch / base commit:** local `main` and `origin/main` at `e2b85cb422e327e0c17268b56ede5a79a649fd79` (initial project commit). Configured `origin`: `https://github.com/justinfox987/DMI-Computation-Pipeline.git`; no fetch or privacy check.

**Handoff owner / branch / scope:** Zoo / `feat/dmi-step1-vectors` / focused review corrections (readback/row identity, pair rotation, penalty/field consistency, loop association, wrapped partner CLI) to local DMI-01 commit `7a5931b`; branched from local committed baseline `56288bf`, not from merged `main`. No branch pushed; one writer.

**Preservation:** before audit, no tracked/staged edits; 6,504 Git-visible untracked file paths under `vasp files/` (ignored paths excluded), plus ignored local `pipeline v3/noq/` runs. The two full VASP distribution copies (6,466 paths, including testsuite data) are now ignored without moving or deleting them; 38 asset paths remain Git-visible and untracked, including the Patch B spec and smaller patch/source collections. Nothing under `vasp files/` was edited or staged. No remote privacy or synchronization check was made.

## Established

- Mathematics Revision 2.4 is complete. Measured vectors replace redundant
  angular state variables; only F1 offset and F2 tilt remain as input controls.
- bcc Fe results and supplied VASP source support direct lab-frame MAGMOM and
  M_CONSTR, with OSZICAR M_int/MW_int readback for the tested setup.
- The historical N0 null trace passed for its recorded files/builds.
- A self-contained Step 1 implementation spec exists.

These statements and the local Step 1 software checks do not establish
production-build acceptance or new BFO results. The tracked N0 manifest records
a historical PASS, but its recorded config/CSO directory paths are absent at
those locations in this checkout; N0 was not replayed.

## Work queue

| ID | Work | Status | Owner / branch | Completion evidence |
|---|---|---|---|---|
| REPO-01 | Reconcile actual repo, baseline and safe tracking boundary | Local handoff and selective VASP-distribution ignore boundary finalized; remote privacy/sync and stale starter wording not verified | Zoo / `docs/repo-baseline-audit` (handoff only) | [Baseline audit](docs/sessions/2026-09-29_2003Z-agent-baseline-audit.md), [finalization](docs/sessions/2026-09-29_2024Z-agent-baseline-finalization.md); untracked source/assets deliberately not staged |
| DMI-01 | Step 1 offline vector migration + corrective review | Local synthetic path and five review corrections implemented; **not production-complete**: no vetted BFO symmetry fixture, trace/parity acceptance or measured noise/covariance | Zoo / `feat/dmi-step1-vectors` (local) | [Implementation log](docs/sessions/2026-09-29_2328Z-agent-dmi-step1-vectors.md), [corrective log](docs/sessions/2026-09-30_0005Z-agent-step1-review-fixes.md), [offline usage](docs/STEP1_LOCAL_USAGE.md); production fit not accepted |
| DMI-02 | Corrected constraint probe and pilot-only runner | Planned after DMI-01 integration | Unassigned | Local runner checks and production smoke-test evidence |
| DMI-03 | Production operator, constraint and F0 pilots | Pending prerequisites | Unassigned | Matched executable/reference and recorded gate results |
| DMI-04 | BFO campaign, paired fit and internal stability checks | Pending pilot results | Unassigned | Accepted dataset, fit and validation report |
| DMI-05 | Independent physical DMI comparisons | Protocol/results outstanding | Unassigned | Matched external-anchor comparisons |

The tracked N0 CLI, OUTCAR-only N0 readback, Patch B indexed dump readers and
first-order trace remain unchanged. A separate versioned Step 1 path supplies
lab targets, OSZICAR sphere readback, signed checks, canonical bond coefficients,
paired diagnostic rows and weighted numerical diagnostics. It cannot certify a
production BFO fit; historical N0 remains schema 2 and unchanged. The legacy
`FRAME_MCONSTR = FRAME_MINT = "unwound"` declaration is N0 forensic metadata,
not a live Step 1 switch. Baseline: 35 tests; current suite: 44 local tests passed
before final handoff checks. Readback and row now recheck input/config/run hashes,
indexed final-loop association and independent gate recomputation; this is not
protection against deliberate file/record reconstruction or authentication of a
production binary, parent restart, trace/basis or reference provenance. No new
VASP run or N0 replay.

## Immediate next action

Review the corrective Step 1 diff and independently inspect actual indexed
production OSZICAR/OUTCAR formatting and final-record association before using
this diagnostic gate for any production campaign. Integrate baseline `56288bf`
and this branch sequentially after remote privacy/synchronization review; do not
push automatically.
Keep the 38 remaining visible untracked VASP asset paths outside staging. Supply
an independently verified canonical BFO bond/orbit basis, production executable
identity, matching converged positive/negative parent and Patch B trace evidence,
then paired replica uncertainty/covariance, P0 and genuine T3 gates before any
accepted fit. Review the [offline usage](docs/STEP1_LOCAL_USAGE.md); the
archived wrong-frame probe table is superseded. Stale starter README/setup
wording belongs to separately scoped integration, not this physics patch.

## Unresolved production inputs

- Remote privacy and cross-machine synchronization have not been checked; do not
  infer a push from the locally configured `origin/main` reference.
- `pipeline v3/acceptance/` paths named in the historical manifest are missing
  at the recorded locations; N0 evidence has not been freshly revalidated.
- Perlmutter executable path/hash and source/build identity.
- Matching reference and job template.
- Validated sphere radii, F1 LZEROZ policy and F2 initialization.
- Paired trace convergence/noise settings and genuine SOC-axis validation.

These are production follow-ups, not reasons to invent values or skip local
implementation/tests. Second-order SOC remains deferred.

## Handoff records

- [Starter-kit preparation](docs/sessions/2026-09-29-bootstrap.md).
- [Local baseline audit and preservation](docs/sessions/2026-09-29_2003Z-agent-baseline-audit.md)
  (historical pre-boundary inventory; other owner entries retained).
- [Local handoff finalization and asset boundary](docs/sessions/2026-09-29_2024Z-agent-baseline-finalization.md)
  on `docs/repo-baseline-audit`; not pushed.
- [DMI-01 local software migration](docs/sessions/2026-09-29_2328Z-agent-dmi-step1-vectors.md); no production acceptance.
- [DMI-01 five-issue corrective review](docs/sessions/2026-09-30_0005Z-agent-step1-review-fixes.md); no production validation.

Keep this file a current snapshot. Detailed commands and attempts belong in
session logs; durable reasons belong in DECISIONS.
