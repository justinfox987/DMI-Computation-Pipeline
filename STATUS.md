# Current project status

**Last reconciled:** 2026-09-29 UTC, from the local checkout, [baseline audit](docs/sessions/2026-09-29_2003Z-agent-baseline-audit.md) and [handoff finalization](docs/sessions/2026-09-29_2024Z-agent-baseline-finalization.md).

**Code checkout inspected:** tracked `pipeline v3/` package, tests, N0 evidence and manifest; no production VASP revalidation.

**Integration branch / base commit:** local `main` and `origin/main` at `e2b85cb422e327e0c17268b56ede5a79a649fd79` (initial project commit). Configured `origin`: `https://github.com/justinfox987/DMI-Computation-Pipeline.git`; no fetch or privacy check.

**Handoff owner / branch / scope:** Zoo / `docs/repo-baseline-audit` / local baseline documents and narrowly scoped ignore rules; branch created from `main`, not pushed. No DMI-01 owner claimed.

**Preservation:** before audit, no tracked/staged edits; 6,504 Git-visible untracked file paths under `vasp files/` (ignored paths excluded), plus ignored local `pipeline v3/noq/` runs. The two full VASP distribution copies (6,466 paths, including testsuite data) are now ignored without moving or deleting them; 38 asset paths remain Git-visible and untracked, including the Patch B spec and smaller patch/source collections. Nothing under `vasp files/` was edited or staged. No remote privacy or synchronization check was made.

## Established

- Mathematics Revision 2.4 is complete. Measured vectors replace redundant
  angular state variables; only F1 offset and F2 tilt remain as input controls.
- bcc Fe results and supplied VASP source support direct lab-frame MAGMOM and
  M_CONSTR, with OSZICAR M_int/MW_int readback for the tested setup.
- The historical N0 null trace passed for its recorded files/builds.
- A self-contained Step 1 implementation spec exists.

These statements do not establish production-build acceptance, new BFO results,
or that the current code implements the revised convention. The tracked N0
manifest records a historical PASS, but its recorded config/CSO directory paths
are absent at those locations in this checkout; this audit did not rerun N0.

## Work queue

| ID | Work | Status | Owner / branch | Completion evidence |
|---|---|---|---|---|
| REPO-01 | Reconcile actual repo, baseline and safe tracking boundary | Local handoff and selective VASP-distribution ignore boundary finalized; remote privacy/sync and stale starter wording not verified | Zoo / `docs/repo-baseline-audit` (handoff only) | [Baseline audit](docs/sessions/2026-09-29_2003Z-agent-baseline-audit.md), [finalization](docs/sessions/2026-09-29_2024Z-agent-baseline-finalization.md); untracked source/assets deliberately not staged |
| DMI-01 | Inspect current code and implement or verify Step 1 | Tracked package is N0-only; Step 1 migration not present or started by audit | Unassigned | Spec acceptance checks and future implementation session |
| DMI-02 | Corrected constraint probe and pilot-only runner | Planned after DMI-01 integration | Unassigned | Local runner checks and production smoke-test evidence |
| DMI-03 | Production operator, constraint and F0 pilots | Pending prerequisites | Unassigned | Matched executable/reference and recorded gate results |
| DMI-04 | BFO campaign, paired fit and internal stability checks | Pending pilot results | Unassigned | Accepted dataset, fit and validation report |
| DMI-05 | Independent physical DMI comparisons | Protocol/results outstanding | Unassigned | Matched external-anchor comparisons |

The tracked `pipeline v3/` package has an N0 CLI, OUTCAR-only N0 readback, Patch B
dump readers, first-order trace and gates. It has no live Step 1 target writer,
OSZICAR sphere reader, vector bond/paired-row kernel or fit CLI. The legacy
`FRAME_MCONSTR = FRAME_MINT = "unwound"` declaration remains. Local synthetic
software suite: 35 passed on Python 3.11.15 / pytest 9.1.1 / NumPy 2.4.6;
these tests do not validate production physics. Check the audit for exact command.

## Immediate next action

Review the [finalization log](docs/sessions/2026-09-29_2024Z-agent-baseline-finalization.md)
and integrate this local handoff branch into `main` after checking remote privacy
and synchronization; do not push automatically. Review the 38 remaining untracked
asset paths deliberately before any future staging, and keep bulk data outside
Git. Correct the stale starter-kit README/setup claims in a separately scoped
documentation integration. After the handoff is integrated, coordinate a DMI-01
owner and start a separate focused Step 1 branch from the updated integration
base (for example `feat/dmi-step1-vectors`), checking for an existing branch
first. Do not treat a STATUS task claim as a distributed lock.

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
- Add a DMI-01 implementation session only when that work actually occurs.

Keep this file a current snapshot. Detailed commands and attempts belong in
session logs; durable reasons belong in DECISIONS.
