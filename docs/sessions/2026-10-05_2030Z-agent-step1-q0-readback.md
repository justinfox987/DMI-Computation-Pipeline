# Session: q0 reference and full historical Fe Step 1 readback

- Session ID / UTC date: 2026-10-05_2030Z-agent-step1-q0-readback; 2026-10-05 UTC.
- Agent or human / platform: Codex / Windows local checkout.
- Task ID and scope: DMI-01; validate the supplied q0 reference, extract its independent sphere norms, prepare a diagnostic reconstruction, and run the complete `step1-read` CLI on the original lambda=1 sample. No VASP rerun, code or tolerance change.
- Branch: `feat/dmi-step1-vectors`, tracking `origin/feat/dmi-step1-vectors`, ahead two local commits at start; no fetch or push.
- Base commit at session start: `ee8299a`.
- Working-tree changes already present: only untracked `vasp files/` assets; preserved. No more-specific AGENTS.md found.
- Related spec / prior session: [Step 1 spec](../dmi_step1_implementation_spec.md), [field/penalty validator handoff](2026-09-30_2011Z-agent-step1-field-penalty-validator.md), and [source audit](2026-09-30_1933Z-agent-step1-field-penalty-source-audit.md).
- Status: complete diagnostic readback with a failed physical gate; no production acceptance.

## Work performed

Inspected the original `vasp files/sample-files/Fe_q0_test/q0/` and `reader_test_2/` files in place. The q0 INCAR requests QSPIRAL `(0,0,0)`, RWIGS 1.5 and lambda zero. The q0 OUTCAR has one completed run, final iteration `(1,20)`, a subsequent EDIFF reached marker and timing footer. The final q0 OSZICAR sphere table is lines 264-266, with both Fe sites `M_int=(2.131,0,0)` and `MW_int=(1.758,0,0)` at displayed precision. [references.json](../../evidence/2026-10-05-fe-q0-step1-readback/references.json) stores `M_int: [2.131,2.131]`, `MW_int: [1.758,1.758]` in site order. They are independent of the lambda=1 sample.

Both POSCAR files are byte identical, including Fe ion order and direct sites `(0,0,0)`, `(0.5,0.5,0.5)`, SHA-256 `91e11367c9d093742a9f166e0b64c22a95db4d34ce7aa51f9a7bc3e98b9665fc`. The OUTCAR reciprocal k-point sections match for all 125 rows. The shared INCAR physics settings checked include Fe_pv PAW, PBE, cutoff 550 eV, NBANDS 56, ISMEAR 0, SIGMA 0.05, EDIFF 1e-7, ALGO All, LASPH, noncollinear spiral, SAXIS z, and RWIGS 1.5; both print the same VASP build banner. Q and lambda differ by design. ICHARG 1 versus 2 is an initial charge difference; LORBIT 2 versus 11 and NCORE/KPAR 8/2 versus 16/4 also differ. q0 omits LZEROZ; the supplied `reader.F` defaults it to true under LSPIRAL, matching the explicit True in the sample. The exact production binary/source identity is unavailable. The [evidence record](../../evidence/2026-10-05-fe-q0-step1-readback/README.md) contains raw reference checksums and detail.

Created [recipe.json](../../evidence/2026-10-05-fe-q0-step1-readback/recipe.json), then used `step1-prepare` to create [prepared/config.json](../../evidence/2026-10-05-fe-q0-step1-readback/prepared/config.json) and its INCAR fragment. The F1 diagnostic `angle_deg=-45` cancels the second Fe site's `+45` degree q phase, reproducing the historical +x/+x MAGMOM and M_CONSTR. This is a reconstruction, not historical family or measurement-axis provenance. The generated config's T/F logical tag spellings do not match the original INCAR's True/False under the existing literal reader comparison. Preserved the generated config and created [historical-config.json](../../evidence/2026-10-05-fe-q0-step1-readback/historical-config.json) with only four logical tag spellings copied from the run INCAR. The first direct read failed with `Run INCAR LNONCOLLINEAR differs from requested input`; the full read with the historical config succeeded at file parsing and wrote a state, then returned exit 1 for the gate.

The final state is at the ignored local path `artifacts/local/2026-10-05-fe-q0-step1-readback/state.json`, SHA-256 `af3e7b80ab14c39b2b6eb5b0389e237ad7a02f849e804c58e364d0093c3a5b28`. It contains local absolute paths and is not staged. The full VASP outputs remain untracked and unstaged. The initial duplicate state under evidence was hash-compared to the ignored output and removed.

| Acceptance check | Result |
|---|---|
| Input/config/OUTCAR echo and final OSZICAR association | PASS; final sample step `(1,32)` |
| Collapsed moments | PASS; none |
| Signed M_int full geometry and transverse phase | PASS; 0.83693 degrees on each site, strict 1 degree limit |
| M_int/MW_int directional agreement | PASS; under 1 degree |
| Absolute MW_int alignment | FAIL; 1.39101 degrees on each site, strict 1 degree limit |
| M_int norm drift versus independent q0 | FAIL; 6.01788% on each site, strict 5% limit |
| MW_int norm drift versus independent q0 | PASS; 3.10206% on each site, strict 5% limit |
| Printed E_p versus printed MW_int precision | PASS |
| Physical penalty | FAIL; 0.0039272 eV versus 0.001 eV limit |
| Signed factor-two field | PASS at printed moment precision |
| Field/penalty identity | UNAVAILABLE as a same-update check; intervals disjoint by at least 2.55506125e-7 eV at matched lambda 1 |
| Overall realization | FAIL: two weighted alignment reasons, one M_int drift reason, one printed penalty reason |

The source audit's cached penalty/later MW refresh is a concrete timing explanation for the disjoint field/penalty intervals in the inspected source path. The sample executable has not been authenticated to that source; no CGA-wide exemption or tolerance increase was applied. The physical realization failure prevents this state from serving as an accepted parent.

## Verification

All CLI commands below ran from `pipeline v3` with `C:/Users/finny/miniconda3/envs/research/python.exe -B -m dmi_pipeline` as the prefix.

| Exact command or evidence source | Result | Scope / limits |
|---|---|---|
| q0 INCAR/OUTCAR/OSZICAR, POSCAR hashes, supplied `reader.F`, and Python `sphere`/`incar` plus 125 OUTCAR k-point row comparison | PASS: reference q, radius, convergence, site order, norm source and settings as recorded above. | Supplied local files; no executable hash or independently verified binary/source match. |
| `step1-prepare --recipe ../evidence/2026-10-05-fe-q0-step1-readback/recipe.json --poscar '../vasp files/sample-files/reader_test_2/POSCAR' --output ../evidence/2026-10-05-fe-q0-step1-readback/prepared` | PASS, exit 0; generated +x/+x diagnostic config and INCAR fragment. | Generated boolean spellings do not match historical INCAR spellings. |
| `step1-read --config ../evidence/2026-10-05-fe-q0-step1-readback/prepared/config.json --run '../vasp files/sample-files/reader_test_2' --references ../evidence/2026-10-05-fe-q0-step1-readback/references.json --output ../evidence/2026-10-05-fe-q0-step1-readback/prepared-attempt-state.json` | EXPECTED INPUT ERROR, exit 1: `Run INCAR LNONCOLLINEAR differs from requested input`; no state written. | Direct generated-config path. |
| `step1-read --config ../evidence/2026-10-05-fe-q0-step1-readback/historical-config.json --run '../vasp files/sample-files/reader_test_2' --references ../evidence/2026-10-05-fe-q0-step1-readback/references.json --output ../artifacts/local/2026-10-05-fe-q0-step1-readback/state.json` | CLI ran to completion, wrote state; exit 1 because physical gate failed for the four reasons above. | Historical config changes only logical spellings. Output is ignored local evidence. |
| Full software suite and VASP rerun | NOT RUN. | No code change or new calculation requested. |

## Decisions or deviations

Used a spelling-only historical config copy because current `step1-read` compares generated `T/F` to the original INCAR's `True/False` literally. The prepared config remains unchanged, and the copy is clearly labelled; no physics, tolerance or source code changed. The state was directed to `artifacts/local/` because it records machine-local absolute paths.

## Handoff

- Completed work: independent q0 norm reference, diagnostic +x/+x preparation, full CLI readback and failed gate with detailed evidence.
- Remaining work / blockers: direct unchanged prepare-to-read workflow needs logical-token equivalence; the historical state fails physical realization. Exact GPU executable/source identity and production BFO prerequisites remain unavailable.
- Next concrete action: correct the reader's logical-tag comparison in a focused code task, then rerun the direct generated-config path. For physical acceptance, obtain a newly converged run satisfying alignment, norm and penalty gates; do not relabel this failed run.
- Files another session should read: this log, the [evidence record](../../evidence/2026-10-05-fe-q0-step1-readback/README.md), generated and historical configs, local ignored state, and both original VASP directories.
- Last tested commit, if available: `ee8299a`; this session ran the CLI against that code, not the software test suite.
- Uncommitted/unpushed work and where it exists: evidence recipe/reference/configs/README, this log, STATUS and CHANGELOG are pending local commit at log creation; `artifacts/local/` state is ignored, and original `vasp files/` assets remain untracked. No push.
