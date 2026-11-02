# Fe F0 pilot preparation review

**2026-10-21 clarification:** this local directory is a generator test. Generate
the real pilot on Perlmutter from explicit cluster paths. Current preparation
requires `--job-template PATH` to include a launch script and never searches the
current directory. The default-discovery behavior described in the historical
2026-10-19 record below is superseded. See the
[Perlmutter sequence](../../docs/PERLMUTTER_F0_PILOT.md); missing local copies of
cluster-only assets do not block local software completion.

Prepared 2026-10-19 with the existing schema-3 target generator and the extended
`step1-prepare` shared-input writer. No VASP job was submitted or executed.

The local pilot is `artifacts/local/2026-10-19-fe-f0-pilot/F0-plus/`. It contains
POSCAR, KPOINTS, POTCAR, INCAR, INCAR.step1 and config.json. All VASP inputs are
present. **The local pilot is for review only:** no working job.sh is available
in this checkout, and the inherited spiral cutoff setting needs a decision.
The user states that the working job.sh will be in the current directory when
they generate F0; the command now copies it by default when present. There is
no placeholder launch script. All local material/pilot files, including POTCAR,
remain under the existing ignored `artifacts/local/` boundary.

## Existing preparation paths and the missing step

| Path | Finding |
|---|---|
| `step1.prepare` | Already generates physical targets, magnetic seeds, constraint tags and schema-3 config from one recipe/POSCAR. Reused. |
| `step1.write_inputs` / `step1-prepare --poscar` | Already writes config and INCAR.step1; fragment-only behavior retained. |
| `realized.incar`, `workflow.INCAR_TAGS` | Existing duplicate/typo parsing and tag whitelist reused for base INCAR. |
| `manifest.save`, `manifest.file_hash` | Existing JSON writing and input identity reused. |
| Archived v2 `materialize.py` | Copies material inputs, but depends on old schemas, target conventions and other dependencies. Inspected for available behavior; not imported into schema 3. |
| Local launch scripts | Archived job.sh is fully commented; the other scripts are examples, probe submission code or a dummy fixture. None establishes a working launch for this pilot. |

The missing live step was assembly: merge generated tags into the shared base
INCAR and copy the three material files plus a supplied launch script. The
existing writer now does this with `--inputs`. Generated tags replace inherited
magnetic tags in the merged INCAR; all other base settings are preserved. Thus
targets, config, INCAR.step1 and final INCAR have a single generator. Missing or
empty required material files fail before output creation, and a nonempty
destination is rejected. A missing default job.sh produces an explicit
review-only message; an explicitly named missing template is an error. Scripts
are copied byte-for-byte and never executed or rewritten.

## Candidate calculation settings

These are reviewable pilot choices, not pinned production settings. The recipe
is [recipe.json](recipe.json); change it and regenerate to change the magnetism.

| Setting | Prepared value / basis |
|---|---|
| Structure / sites | bcc Fe2, cubic lattice 2.86303549895 Angstrom; direct `(0,0,0)` and `(0.5,0.5,0.5)`; magnetic indices `[0,1]` |
| Family / side / signs | F0, positive side, `[+1,+1]` as a ferromagnetic candidate consistent with the q0 reference; no AFM signs imposed |
| QSPIRAL | `(0.25,0,0)` reciprocal fractional, inherited finite-q pilot point |
| Physical M_CONSTR | Fe1 `(1,0,0)`; Fe2 `(0.70710678118655,0.70710678118655,0)` |
| MAGMOM | Fe1 `(2.2,0,0)`; Fe2 `(1.55563491861,1.55563491861,0)` |
| Constraint | mode 1, lambda 1.0, RWIGS 1.5 Angstrom; lambda carried from sample, not validated for this F0 state |
| Spin convention | noncollinear, LSPIRAL T, LSORBIT F, SAXIS `(0,0,1)`, LZEROZ T; axis z is diagnostic bookkeeping |
| Start / ionic state | ISTART 0, ICHARG 2, NSW 0, IBRION -1; cold start, no WAVECAR/CHGCAR required |
| Functional / potential | PBE, LASPH T, GGA_COMPAT F; PAW_PBE Fe_pv 02Aug2007, one dataset, ZVAL 14 |
| Basis / bands | inherited ENCUT 550 eV, NBANDS 56, LREAL F; **cutoff unresolved** |
| Mesh / smearing | Gamma 5x5x5, ISMEAR 0, SIGMA 0.05 eV |
| SCF | ALGO All, EDIFF 1e-7 eV, NELM 125, NELMIN 1, ISYM -1, LMAXMIX 4 |
| Projection / resources | LORBIT 11; inherited NCORE 16, KPAR 4 require reconciliation with the supplied GPU job script |

The historical sample's OUTCAR lines 125-127 warn that ENINI=550 eV requires
ENMAX >575.402 eV, while ENMAX is 550 eV. Preparation retains the shared cutoff
and does not claim that warning is resolved. Decide the ENCUT/ENINI combination
and convergence protocol before running; changing numerical settings may also
require a matching q0 magnitude reference. Review the selected q, signs and
lambda rather than treating the draft as an accepted choice. The exact GPU
executable, hash, account, resources, modules and binding are not available
locally; they must come from the working job.sh and its environment. A copied
script alone does not authenticate the binary or certify successful execution.

## Inputs, command and identity

The ignored `shared/` directory next to the pilot contains POSCAR, KPOINTS and
POTCAR copied unchanged from `vasp files/sample-files/Fe_q0_test/q0/`. Its base
INCAR was copied from `vasp files/sample-files/reader_test_2/INCAR`, changing
only SYSTEM from BFO-ferro to Fe-F0-pilot-review. Original VASP files were
preserved. Magnetic entries in that base are replaced by recipe generation.

From `pipeline v3` the actual command was:

```powershell
& 'C:/Users/finny/miniconda3/envs/research/python.exe' -B -m dmi_pipeline step1-prepare --recipe '../evidence/2026-10-19-fe-f0-preparation/recipe.json' --inputs '../artifacts/local/2026-10-19-fe-f0-pilot/shared' --output '../artifacts/local/2026-10-19-fe-f0-pilot/F0-plus'
```

It exited 0 for successful input writing and explicitly reported the missing
job.sh and review-only status. To generate a complete directory later, use a
new empty output path from a current directory containing the working job.sh,
or pass `--job-template path/to/job.sh`. No command submits a job.

| File | SHA-256 |
|---|---|
| Original reader_test_2/INCAR | `908ba39fc447999147cbdeb9d8f2688cc575a5e2c075b7c8f799f9570fa09e30` |
| Pilot POSCAR (identical to q0 source) | `91e11367c9d093742a9f166e0b64c22a95db4d34ce7aa51f9a7bc3e98b9665fc` |
| Pilot KPOINTS (identical to q0 source) | `57bf7398bb19eff159f87b528dbf046816185eb0abce77d560cb0aa8db867ddf` |
| Pilot POTCAR (identical to q0 source) | `e96179f13e87664e48aed485c2113db4b894f4702180a1840e8206974d0cd1f5` |
| Pilot config.json | `050501849085794edb4f2cb5844c0e72eeb57ce0dc2e36d75a7991c65a05a2d0` |
| Pilot INCAR | `640b6cebec31e14e2068a3c3abae4da18e6db89f671ebd1300b922285cdb739b` |
| Pilot INCAR.step1 | `c14b0f5a362aab6e7c3a0045a4b2a0f4a3305704ffef1efc352a440815ea152e` |

Verification: generated INCAR tags match config exactly; printed MAGMOM and
M_CONSTR agree with the generated vectors; material copies match source bytes.
The focused software suite passed 20 tests and the final full suite passed 55.
There are no run outputs or new realization/production acceptance claims.
