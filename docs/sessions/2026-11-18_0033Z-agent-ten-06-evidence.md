# Session: TEN-06-EV, the Fe pilot diagnostics and verdict

- Session ID / UTC date: 2026-11-18 (task dated 2026-11-17 by the user)
- Agent or human / platform: Claude Code (Opus 5.5), WSL2
- Task ID and scope: TEN-06-EV, completing `evidence/2026-11-17-fe-ten06-pilot/README.md` with the diagnostics run after FIT-1; docs only
- Branch: `ten-06-evidence`, from `main`
- Base commit at session start: `138c3c0` (PR #24 merge)
- Working-tree changes already present: untracked `Claude outputs/` and `materials/fe/job.sh` (not this task's; left untouched)
- Related spec / prior session: the user's TEN-06-EV task text (2026-11-17); [FIT-1 log](2026-11-17_1855Z-agent-fit-1-model-check.md)
- Status: complete, awaiting review

## Work performed

- `evidence/2026-11-17-fe-ten06-pilot/README.md`: "Diagnostics after Gate 2"
  (a hypothesis table and the two seven-point t scans with the reviewer's
  model comparisons), "Open question", a new "Verdict" and "Implication for
  metals". The 24x24x24 placeholder now reads "result not supplied"; the hand
  check's "most likely cause" and Gate 2.7 point to the diagnostics.
- `plans/ten-06-fe-pilot.md`: the status line only.
- `STATUS.md`: TEN-06 done and closed by the user, FIT-1 merged, a new
  Established row for the non-quadratic Fe energies, next action the TEN-07
  spec, the Unresolved entry on Fe rewritten.
- `CHANGELOG.md`.

## Verification

| Exact command or evidence source | Result | Scope / limits |
|---|---|---|
| numpy recomputation of g/t², the local exponents and the three model fits from the two seven-point tables | Agree with the supplied values (A 314.4/288/192 and 324.5/298/199; worst residuals 0.555/0.306/0.041 and 0.565/0.316/0.078 meV) | Arithmetic from the supplied g only. The ISMEAR 1 g/t² at t = 0.02 computes to 855.25, supplied as 855.3 |
| Tiny-q difference -16.53056495 - (-16.53056019) eV | -4.76 μeV, supplied as -4.8 | Arithmetic only |
| "+0.9 meV per cell" jump estimate | The constant of `c + A t² + B t⁴` on the ISMEAR 0 scan is 0.49 meV per site, 0.98 meV per cell; the record keeps the reviewer's "about +0.9" | The reviewer's own basis is not stated |
| Tests | NOT RUN | Docs only; no code changed |

No VASP run, no cluster contact. Every number in the new sections is from the
user's runs or the reviewer's hand calculations, as supplied in the task.

## Decisions or deviations

- The 24x24x24 diagnostic had a placeholder; no result was supplied, so it is
  recorded as "not supplied", and the 18x18x18 tree as the k-sampling test.
- The spiral-cutoff row records only the A shift at 8x8x8 (442.8 to 429.0):
  no residual exists at the old cutoffs, because those fits ran before FIT-1.
  The open question says so beside "cutoff-independent".
- The task's common settings (NBANDS 40, PREC Normal) are stated for the
  diagnostics; the earlier k series is still described as "NBANDS reduced by
  the user".
- The "As run" paragraph of the TEN-06 spec still says the 24x24x24
  diagnostic is running; the task allowed the status line only, so the status
  line says it gave no recorded result.

## Handoff

- Completed work: TEN-06-EV as specified.
- Remaining work / blockers: review and merge; the TEN-07 spec.
- Next concrete command or action: draft `plans/ten-07-*.md` for the user's approval.
- Files another session should read: the evidence README, STATUS.
- Last tested commit, if available: not applicable (docs only).
- Uncommitted/unpushed work and where it exists: none of this task's after the push.
