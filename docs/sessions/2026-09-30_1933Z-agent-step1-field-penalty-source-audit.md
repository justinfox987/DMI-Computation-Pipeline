# Session: Lambda=1 field and penalty source audit

- Session ID / UTC date: 2026-09-30_1933Z-agent-step1-field-penalty-source-audit; 2026-09-30 UTC.
- Agent or human / platform: Codex / Windows local checkout; read-only source and original-file investigation.
- Task ID and scope: DMI-01, only the remaining printed field versus penalty discrepancy in the constrained Fe sample. No parser, gate, tolerance, VASP source, sample or executable changes.
- Branch: `feat/dmi-step1-vectors`, tracking `origin/feat/dmi-step1-vectors`, ahead one local commit; no fetch or push.
- Base commit at session start: `b9a3b095957eacca9261fc6b84f99251c3eb3ebc`.
- Working-tree changes already present: modified `STATUS.md`, untracked `docs/sessions/2026-09-30_1919Z-agent-step1-lambda1-real-file-audit.md`, and untracked `vasp files/`; preserved all. No more-specific AGENTS.md found.
- Related spec / prior session: [math Revision 2.4](../math/heide_math_v2.tex) Section 4, [Step 1 spec](../dmi_step1_implementation_spec.md) Section 5.2, and [preceding real-file audit](2026-09-30_1919Z-agent-step1-lambda1-real-file-audit.md).
- Status: complete as a source and printed-output investigation; no production binary provenance or VASP acceptance established.

## Work performed

Inspected the supplied VASP 6.4.2 source in place, particularly `vasp files/vasp.6.4.2-heide-cpu/src/{constrmag,electron_all,main,pot}.F`, the original `reader_test_2/{INCAR,OUTCAR,OSZICAR}`, and the existing Step 1 validator. The `constrmag.F` copy in `vasp-heide-patch-NEW/src/` and the `vasp-heide-patch/build/ncl/` copy have the same SHA-256 as the inspected source. This is source consistency, not proof that the sample's GPU executable was built from those bytes. No file under `vasp files/` was changed or staged.

**Coefficient:** `constrmag.F:115-116` initializes its private saved `LAMBDA` to zero and reads the requested INCAR value through `PROCESS_INCAR`. A search of assignments in this module found no later mutation. The original INCAR and OUTCAR echo both say `LAMBDA = 1.0`; the module's output format prints only three mantissa decimals as `0.100E+01`. In the supplied source path there is no basis for an actual coefficient near the `1.0000890763` that would make the final field and penalty numerically equal if they represented one moment update. The source alone does not authenticate the exact run executable.

**Shared formula, different update timing:** `constrmag.F:468-545` writes the weighted sphere moments into saved `MW` from a density passed to `M_INT`. For mode 1, `E_CONSTRAINT` computes `E_PENALTY=lambda*sum(|MW_perp|^2)` into a saved variable (`constrmag.F:714-753`). `WRITE_CONSTRAINED_M(...,.TRUE.)` prints that saved penalty but calculates `2*lambda*MW_perp` afresh from the current `MW` (`constrmag.F:779-825`). The header says `lambda*MW_perp`, but the code explicitly multiplies by two. `pot.F:299-305` refreshes `MW` whenever `POTLOK` invokes `M_INT`.

The sample uses `ALGO = All`, has `CGA` electronic rows, `ICHARG = 2`, and reports that charge and potential are updated. In the active `ELMIN_ALL` path, the electronic step calls `E_CONSTRAINT` and prints a short penalty/sphere block (`electron_all.F:563-569`); later it calls `SET_CHARGE` and sets `INFO%LPOTOK=.FALSE.` (`electron_all.F:681-705`). After electronic optimization, `main.F:3510-3522` calls `POTLOK` for that pending update; `pot.F` thereby refreshes `MW`. `main.F:3714-3740` then prints the ionic summary and long constraint block. No intervening `E_CONSTRAINT` call refreshes `E_PENALTY`. Thus the final penalty and final signed fields **are not guaranteed to use the same moment/density update** in this path: the penalty is cached from the electronic step and the fields use the later `MW`. The terminal `E_p` repeats the preceding short-block value, consistent with that sequence. This source path provides a concrete explanation for a small difference, without claiming the unprinted moment change was directly measured.

**Independent printed arithmetic at known lambda 1:** final fields are `(0,-0.088629,0)` and `(0,+0.088629,0)`; final `E_p=0.0039272` eV. Their same-update identity would give `sum(|B_c|^2)/(4*1)=0.0039275498205` eV, a difference of `3.498205e-7` eV. With field rounding of `±0.0000005` per y value, the identity lies in `[0.003927505506125,0.003927594135125]` eV. The printed penalty interval is `[0.00392715,0.00392725]` eV. These intervals do not overlap; the minimum gap is `2.55506125e-7` eV. Coarse printed lambda must not be used to claim strict same-update consistency when the independent INCAR value and source coefficient path are known. The equivalent difference in inferred per-site transverse moment is about `1.97e-6`, below the three-decimal `MW_int` resolution; that is a scale comparison, not a measured density change.

**Separate factor/sign result:** the printed `MW_int,y` values `-0.044` and `+0.044` imply fields near `-0.088` and `+0.088` at lambda 1 for a factor-two, same-sign convention. The final fields have those signs and magnitudes within the moment printing interval. Factor one or reversed signs are excluded at this precision. This evidence does not make the strict field/penalty identity pass.

The current offline validator in `pipeline v3/dmi_pipeline/step1.py:462-499` uses the *printed* lambda half-step of 0.005 in its field/penalty interval and combines factor-two and penalty consistency into one pass label. That permissive printed-value diagnostic must not be cited as strict consistency for this source-identified lambda=1 run. No validator behavior was changed in this investigation; before any production acceptance claim, the diagnostic should distinguish sign/factor evidence, known-coefficient same-update identity, and the source's update timing without widening a tolerance to force a pass.

## Verification

| Exact command or evidence source | Result | Scope / limits |
|---|---|---|
| `rg -n` and numbered `Get-Content` reads of `constrmag.F`, `electron_all.F`, `main.F`, `pot.F` and original run inputs/outputs | PASS: formulas, call order, printed formats, and requested/echoed lambda located as cited above. | Supplied local source and original sample; exact executable/source identity not verified. |
| `Get-FileHash ... -Algorithm SHA256` for three `constrmag.F` copies | PASS: all `3EC6F8B81FCFB4E0224B2EF5194ADCE59A2FC17E35B3D43A8A5F6B44A3370A2B`. | Shows local copies agree, not run binary provenance. |
| `C:/Users/finny/miniconda3/envs/research/python.exe -B -c` using `decimal.Decimal` on final field, penalty and their displayed half-units | PASS: field identity and penalty intervals disjoint by at least `2.55506125e-7` eV at lambda exactly 1. | Printed-output arithmetic; underlying full-precision moments were not available. |
| `git diff --check`; Python read of this new log for trailing whitespace and final newline; `git status --short --branch` | PASS: no whitespace error; new log has final newline; only STATUS/CHANGELOG and the two audit logs are changed beyond pre-existing untracked VASP assets. | Documentation scope and preservation check; no staging or commit. |
| VASP rerun, executable hash/build match, full schema-3 `step1-read`, production gate and test suite | NOT RUN. | Outside this source-only discrepancy investigation. |

## Decisions or deviations

None. No formula or tolerance was changed. The source timing finding qualifies the prior read-only audit's coarse-lambda caveat; it does not supersede the Step 1 physical convention.

## Handoff

- Completed work: established the source's cached-penalty versus refreshed-moment print path, fixed coefficient path, disjoint exact-lambda intervals, and separate factor/sign evidence.
- Remaining work / blockers: exact sample executable/source identity and unprinted per-update moments are unavailable. Other realization gates and production evidence remain as recorded in STATUS and the prior audit.
- Next concrete action: if validating this executable, obtain its source/build identity and capture or recompute penalty and fields from one documented `MW` update; keep current printed identity marked inconsistent at exact lambda 1.
- Files another session should read: this log, the preceding real-file audit, `constrmag.F`, `electron_all.F`, `main.F`, `pot.F`, and original `reader_test_2` outputs.
- Last tested commit, if available: `b9a3b095957eacca9261fc6b84f99251c3eb3ebc`; no software tests were run in this source-only audit.
- Uncommitted/unpushed work and where it exists: this log, minimal STATUS/CHANGELOG handoff, prior uncommitted audit documentation and all untracked VASP assets remain local; no push or staging.
