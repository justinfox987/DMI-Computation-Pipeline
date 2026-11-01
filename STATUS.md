# Current project status

**Last reconciled:** 2026-10-21 UTC on local `feat/dmi-step1-vectors`; the [Perlmutter portability handoff](docs/sessions/2026-10-21_1815Z-agent-perlmutter-pilot-portability.md) makes pilot template selection explicit and documents cluster generation/submission/readback. The local F0 directory is a generator test. Cluster-only assets are supplied on Perlmutter, not prerequisites for local software completion. No submission or push in this session.

**Code checkout inspected:** tracked `pipeline v3/` reader and tests, status/usage/spec and original Fe files. A full Step 1 CLI readback now exists for the lambda=1 sample with a converged q0 norm reference; its realization gate fails. No production VASP acceptance or N0 replay.

**Integration branch / base commit:** local `main` and `origin/main` at `e2b85cb422e327e0c17268b56ede5a79a649fd79` (initial project commit). Configured `origin`: `https://github.com/justinfox987/DMI-Computation-Pipeline.git`; no fetch or privacy check.

**Handoff owner / branch / scope:** Codex / `feat/dmi-step1-vectors` / explicit Perlmutter interfaces for the single F0 preparation/launch/readback sequence, preserving prior physics and reader checks. No new scheduler or submission. Initial HEAD `bbea7ef` was one commit ahead of the local tracking reference; no fetch or remote verification. One writer in this checkout.

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
| DMI-01 | Step 1 offline vector migration + real-file reader follow-up | Reader repair, field/penalty diagnostic and logical input comparison fixes have local evidence. Full CLI readback of historical Fe run using the unmodified prepared config and converged q0 norm reference **fails** weighted alignment, M_int drift and penalty gates. **Not production-complete**: no vetted BFO symmetry fixture, trace/parity acceptance or measured noise/covariance | Codex (current), Zoo (prior) / `feat/dmi-step1-vectors` (local) | [logical comparison handoff](docs/sessions/2026-10-19_1556Z-agent-step1-logical-readback.md), [q0 readback handoff](docs/sessions/2026-10-05_2030Z-agent-step1-q0-readback.md), [evidence record](evidence/2026-10-05-fe-q0-step1-readback/README.md), [offline usage](docs/STEP1_LOCAL_USAGE.md); no production fit accepted |
| DMI-02 | Corrected constraint probe and pilot-only runner | Single-pilot preparation/readback interfaces verified locally. Explicit material/recipe/template/output paths; executable/resources remain configured by the working cluster script. Current-directory script discovery removed. Cluster generation, ordinary sbatch submission and readback sequence documented; real smoke test and broader probe/campaign runner remain outstanding | Codex / `feat/dmi-step1-vectors` for single-pilot interface | [Portability handoff](docs/sessions/2026-10-21_1815Z-agent-perlmutter-pilot-portability.md), [Perlmutter sequence](docs/PERLMUTTER_F0_PILOT.md); 55 local tests pass, no job submitted |
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

Transfer/install the tested code, then follow the [Perlmutter pilot sequence](docs/PERLMUTTER_F0_PILOT.md)
with explicit cluster material, recipe, job-template, executable and output paths.
The [local F0 candidate](evidence/2026-10-19-fe-f0-preparation/README.md) is only
a generator test. Decide q/signs/lambda and ENCUT/ENINI, resolve the historical
spiral warning, and reconcile NCORE/KPAR with the working script on Perlmutter.
Supply that script via `--job-template`; current-directory discovery is removed.
Review cluster identities and syntax before a later user submission. Then perform
the real launch/convergence/readback checks. Missing local copies of cluster
assets do not block software completion; numerical settings and executable/build
validation remain unresolved scientific/cluster checks.

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
and penalty acceptance limits remain. The [2026-10-05 q0 readback](docs/sessions/2026-10-05_2030Z-agent-step1-q0-readback.md)
supplied a reconstructed schema-3 configuration and independent same-definition,
same-RWIGS `M_int` and `MW_int` reference norms. The full CLI gate failed
absolute MW_int alignment on both sites (1.391 degrees), M_int norm drift
(6.018% versus 5%), and printed penalty
(0.0039272 eV versus 0.001 eV). The independent reference is converged at q0
with matching POSCAR and RWIGS. The [logical comparison follow-up](docs/sessions/2026-10-19_1556Z-agent-step1-logical-readback.md)
reused the existing strict parser so the unmodified prepared T/F config now
reads the historical True/False INCAR. Its CLI gate reproduces the same four
physical rejection reasons, with no threshold change. Preserve both failed
states as diagnostic evidence; a new physically realized parent is required.
Verify production indexed files/build before any campaign; the OUTCAR
iteration-order sentence in [offline usage](docs/STEP1_LOCAL_USAGE.md)
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
- Matching production reference and job template (the diagnostic Fe q0 reference does not cover BFO production).
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
- [DMI-01 q0 reference and full historical Fe readback](docs/sessions/2026-10-05_2030Z-agent-step1-q0-readback.md); independent reference norms and failed physical gate recorded, with generated-config logical spelling limitation and ignored local state path. No VASP rerun.
- [DMI-01 strict logical comparison and direct prepared-config readback](docs/sessions/2026-10-19_1556Z-agent-step1-logical-readback.md); 19 focused and 54 total local tests pass, unmodified prepared config reaches the same failed physical gate, no VASP rerun.
- [Single Fe F0 pilot preparation](docs/sessions/2026-10-19_1627Z-agent-fe-f0-preparation.md); reused target generation, extended shared-input writing and default current-directory job.sh copying, prepared review-only local input directory; 20 focused and 55 total local tests pass, no VASP execution.
- [Explicit Perlmutter pilot interfaces](docs/sessions/2026-10-21_1815Z-agent-perlmutter-pilot-portability.md); supersedes current-directory template discovery, supports explicit ENINI through the existing whitelist, documents generation/sbatch/readback and host provenance; 55 local tests and runbook Bash syntax pass, no cluster execution.
- [Perlmutter Fe pilot runner T0 baseline audit](docs/sessions/2026-10-30_1516Z-agent-pilot-runner-t0-baseline.md); Zoo / `feat/dmi-step1-vectors`: 55 passed, five reported claims verified with historical physical rejection retained; corrected the untracked T0..T6 plan for T1 extraction, q0/two-case import and T5 launch provenance; next T1 check-run extraction, no cluster execution or commit.
- [Perlmutter Fe pilot runner T1 check-run extraction](docs/sessions/2026-10-30_1526Z-agent-pilot-runner-t1-check-run.md); Zoo / `feat/dmi-step1-vectors`: shared config-free OUTCAR/OSZICAR convergence and final-step check extracted, exact pre/post synthetic readback including provenance matched, 62 local tests pass (55 baseline + 7 new); next T2 campaign planning on this branch with one writer, no VASP/cluster execution or push; cluster-only physical validation remains blocked on actual inputs/build/run.
- [Perlmutter Fe pilot runner T2 campaign preparation](docs/sessions/2026-10-30_1538Z-agent-pilot-runner-t2-campaign.md); Zoo / `feat/dmi-step1-vectors`: offline two-case schema/plan, explicit dependency split, strict pre-write validation, real single-recipe expansion and synthetic CLI tests; 62 baseline -> 106 total local tests pass. Next T3 independent q0 reference extraction/preparation/compatibility; generated-reference mode is plan-only until T3. No VASP, submission, cluster contact or push; unrelated untracked `vasp files/` untouched.
- [Perlmutter Fe pilot runner T3 independent reference](docs/sessions/2026-10-30_1559Z-agent-pilot-runner-t3-reference.md); Zoo / `feat/dmi-step1-vectors`: generated q0 preparation, converged q0 extraction/provenance and pre-acceptance compatibility for imported and generated references; 106 baseline -> 136 local tests pass. Next T4 submission/status/resume must enforce verified reference status and recheck input provenance before releasing acceptance; no VASP, cluster contact or push; unrelated `vasp files/` untouched.
- [Perlmutter Fe pilot runner T4a submit-path handoff](docs/sessions/2026-10-30_2124Z-agent-pilot-runner-t4a-submit-path.md); Zoo / `feat/dmi-step1-vectors` single writer: local T4 baseline committed with prepared Slurm jobsall, pinned hashes, fake-scheduler idempotency/restart/argv tests (153 -> 160 local tests, `bash -n` pass). Next T4b: reconcile/readback/resume issues and hash/live-job regression tests; T5 still owns frozen code/executable evidence. No VASP, Slurm/cluster contact or push; `vasp files/` untouched.

Keep this file a current snapshot. Detailed commands and attempts belong in
session logs; durable reasons belong in DECISIONS.
