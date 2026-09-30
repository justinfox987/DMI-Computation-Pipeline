# Current project status

**Last reconciled:** 2026-09-30 UTC on local `feat/dmi-step1-vectors`, starting from `b9a3b09`; the [field/penalty validator handoff](docs/sessions/2026-09-30_2011Z-agent-step1-field-penalty-validator.md) and supporting audits are committed locally. It applies the preceding [source audit](docs/sessions/2026-09-30_1933Z-agent-step1-field-penalty-source-audit.md) after the [second real-file lambda=1 audit](docs/sessions/2026-09-30_1919Z-agent-step1-lambda1-real-file-audit.md). Earlier reader, implementation and baseline logs remain linked below. No push.

**Code checkout inspected:** tracked `pipeline v3/` reader and tests, existing status/usage/spec and original Fe file observations from both read-only sample checks; no production VASP acceptance, N0 replay or full Step 1 CLI read.

**Integration branch / base commit:** local `main` and `origin/main` at `e2b85cb422e327e0c17268b56ede5a79a649fd79` (initial project commit). Configured `origin`: `https://github.com/justinfox987/DMI-Computation-Pipeline.git`; no fetch or privacy check.

**Handoff owner / branch / scope:** Codex / `feat/dmi-step1-vectors` / field-versus-penalty validator follow-up, preserving Zoo's parser/test review and local commit starting at `99b26ee`. Branch descended from local committed baseline `56288bf`, not merged `main`. No push; one writer in this checkout.

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
| DMI-01 | Step 1 offline vector migration + real-file reader follow-up | Reader repair and field/penalty diagnostic follow-up committed locally. Original Fe OSZICAR parses, but its requested +x state is physically misaligned and no versioned config/reference-bound read or production gate was run. **Not production-complete**: no vetted BFO symmetry fixture, trace/parity acceptance or measured noise/covariance | Codex (current), Zoo (prior) / `feat/dmi-step1-vectors` (local) | [Field/penalty validator handoff](docs/sessions/2026-09-30_2011Z-agent-step1-field-penalty-validator.md), [real-sample reader log](docs/sessions/2026-09-30_1610Z-agent-step1-reader-real-sample.md), [implementation](docs/sessions/2026-09-29_2328Z-agent-dmi-step1-vectors.md), [offline usage](docs/STEP1_LOCAL_USAGE.md); no production fit accepted |
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
not a live Step 1 switch. Baseline: 35 tests; focused parser review:
17 focused and 52 total local tests passed before the local commit.
Readback and row recheck input/config/run hashes,
indexed final-loop association, exact QSPIRAL shape, matching pair RWIGS and
independent gate recomputation. Zero/small transverse fields do not certify a
factor-two convention. Original Fe OSZICAR has 95 sphere tables for one ionic
summary; terminal sphere rows 714–716 and OUTCAR `Iteration 1(50)` match the
last electronic loop, with OUTCAR EDIFF and timing markers present. This is a
read-only parser/format observation, not a schema-3 config/reference-bound gate.
The requested both-Fe +x inputs are distinct from the F0 physical Fe2 target
and measured moments deviate about 22.67 degrees from +x; zero lambda/field
cannot establish the nonzero-lambda convention. These checks are not
protection against deliberate file/record reconstruction or authentication of a
production binary, parent restart, trace/basis or reference provenance. No new
VASP run or N0 replay.

## Immediate next action

Verify intended Fe site signs/settings and resolve the cutoff warning and
requested-target mismatch for both samples. The [lambda=1 read-only audit](docs/sessions/2026-09-30_1919Z-agent-step1-lambda1-real-file-audit.md)
found 59 tables, final ionic/electronic step (1,32), 38 echo tags, signed factor-two
fields consistent at printed-moment precision; MW_int alignment (~1.391°) and
E_p (0.0039272 eV) miss nominal thresholds. The [focused source audit](docs/sessions/2026-09-30_1933Z-agent-step1-field-penalty-source-audit.md)
found that supplied mode-1 source reads LAMBDA=1.0 without a later update,
caches E_p before a final density/potential refresh of MW, then prints fields
from current MW. At exact lambda 1, field-implied and printed E_p intervals
are disjoint by at least 2.55506125e-7 eV: factor/sign evidence is retained,
but strict same-update numeric consistency fails. The local source is not an
authenticated match to the sample's executable. The [validator follow-up](docs/sessions/2026-09-30_2011Z-agent-step1-field-penalty-validator.md)
now records the signed factor result and the disjoint identity intervals
separately at the matched requested coefficient. Identity status stays
unavailable for same-update interpretation until that association is evidenced;
no CGA-wide exemption or tolerance increase was added. The nominal alignment
and penalty acceptance limits remain. Supply a matching schema-3
configuration and independent same-definition, same-RWIGS `M_int` and `MW_int`
reference norms; only then run `step1-read` to an approved output path and report
observed gates (never assume PASS). Verify production indexed files/build before
any campaign; the OUTCAR iteration-order sentence in [offline usage](docs/STEP1_LOCAL_USAGE.md)
was corrected in the earlier local commit.
Integrate baseline `56288bf` and this branch sequentially after remote
privacy/synchronization review; do not push automatically. Keep untracked VASP
assets outside staging. Supply an independently verified canonical BFO bond/orbit
basis, matching converged positive/negative parent and Patch B trace evidence,
then paired replica uncertainty/covariance, P0 and genuine T3 gates before any
accepted fit. The archived wrong-frame probe table is superseded. Stale starter
README/setup wording belongs to separately scoped integration.

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
- [DMI-01 three-issue final review follow-up](docs/sessions/2026-09-30_0024Z-agent-step1-final-review.md); synthetic checks only.
- [DMI-01 original Fe reader-format validation and documentation handoff](docs/sessions/2026-09-30_1610Z-agent-step1-reader-real-sample.md); original lambda=0 files parsed read-only, no config-bound readback or production acceptance.
- [DMI-01 second real-file lambda=1 read-only audit](docs/sessions/2026-09-30_1919Z-agent-step1-lambda1-real-file-audit.md); printed factor-two/sign supported at moment precision, field/penalty caveat and failing nominal alignment/penalty recorded; no production acceptance.
- [DMI-01 field/penalty source audit](docs/sessions/2026-09-30_1933Z-agent-step1-field-penalty-source-audit.md); source shows cached penalty and later MW refresh, fixed LAMBDA path, and exact-lambda printed interval mismatch; no source/binary authentication or production acceptance.
- [DMI-01 field/penalty validator follow-up](docs/sessions/2026-09-30_2011Z-agent-step1-field-penalty-validator.md); signed factor and numerical identity separated without loosening bounds; 18 focused and 53 total local tests passed, no VASP rerun.

Keep this file a current snapshot. Detailed commands and attempts belong in
session logs; durable reasons belong in DECISIONS.
