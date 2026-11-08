# Session: TEN-02 symmetry module

- Session ID / UTC date: 2026-11-08 17:35Z
- Agent or human / platform: Claude Code (Opus 5.5), WSL2
- Task ID and scope: TEN-02, as specified in `plans/ten-02-symmetry.md`
- Branch: `ten-02-symmetry`
- Base commit at session start: `main` at `c660cab`
- Working-tree changes already present: none (clean)
- Related spec / prior session: [spec](../../plans/ten-02-symmetry.md), [handoff](2026-11-08_1710Z-agent-claude-code-handoff.md)
- Status: complete, pending review and merge

## Work performed

- `pipeline v3/dmi_pipeline/symmetry.py` (new, 108 lines): `operations`,
  `spiralization_basis`, `stiffness_basis`, `twist_count`, `exchange_classes`,
  following the spec's conventions and three guards.
- `pipeline v3/dmi_pipeline/realized.py`: `poscar(path) -> (lattice, species, tau)`
  replaces `poscar_species`. It applies the scale factor, accepts Direct with or
  without Selective dynamics, and rejects Cartesian and negative or three-value scales.
- `pipeline v3/dmi_pipeline/step1.py`: `positions` removed; its two callers and the
  `read_state` species check now use `realized.poscar`. There is now one POSCAR
  parser. `read_state` now also parses positions in the run POSCAR. The run POSCAR
  is a hash-checked copy of the input POSCAR, which was already read that way.
- `pipeline v3/pyproject.toml`: `spglib>=2.6`. Installed 2.8.0 in the venv.
- `pipeline v3/tests/test_symmetry.py`: the three tests the spec lists, and nothing more.
- `README.md` (test count, spglib note), `STATUS.md`, `CHANGELOG.md`.

## Verification

| Exact command or evidence source | Result | Scope / limits |
|---|---|---|
| `.venv/bin/python -m pytest -q` (in `pipeline v3`, before changes) | PASS, 13 | Baseline |
| `.venv/bin/python -m pytest -q` (in `pipeline v3`, after changes) | PASS, 16 | spglib emits the expected `DeprecationWarning` |
| Scratch table script importing the test structures | PASS | Every row of the spec's expected-results table matches (below) |
| Fault injection, each run against `tests/test_symmetry.py` | 9 of 9 caught | See the list below |

Reproduced table, using spglib 2.8.0 and numpy 2.5.4:

| System | Pattern | Group | Total | Kept | `p_D` | `p_A` | `n_twist` |
|---|---|---|---:|---:|---:|---:|---:|
| bcc Fe primitive | FM | `Im-3m` | 48 | 48 | 0 | 1 | 0 |
| bcc Fe 2-site | FM | `Im-3m` | 96 | 96 | 0 | 1 | 0 |
| bcc Fe 2-site | G-type | `Im-3m` | 96 | 96 | 0 | 1 | 0 |
| fcc 4-site | FM | `Fm-3m` | 192 | 192 | 0 | 1 | 0 |
| fcc 4-site | `+ + - -` | `Fm-3m` | 192 | 64 | 0 | 2 | 0 |
| fcc 4-site | `+ - - -` | `Fm-3m` | 192 | 48 | 0 | 1 | 0 |
| FeGe B20 | FM | `P2_13` | 12 | 12 | 1 | 1 | 1 |
| BFO | G-type | `R3c` | 6 | 6 | 1 | 2 | 0 |
| Strained zincblende, conventional | FM | `I-4m2` | 32 | 32 | 1 | 2 | 0 |
| Strained zincblende, primitive | FM | `I-4m2` | 8 | 8 | 1 | 2 | 0 |

Both zincblende cells give `D diag(1, -1, 0)`. Rotating the primitive lattice by a
random orthogonal `Q` rotates the `D` projector to within 4e-16. The test checks
the conventional total of 32, which the spec left as "see below".

Faults injected, each caught by at least one test: drop `det(R)`; invert `pi` in
`operations`, which the site-distance guard also trips; invert `pi` in
`twist_count` only (FeGe gives 9, not 1); use `W` in place of `W.T` in the site
map; skip the keep test; remove each of the three guards; use `L = lattice`. The
source file was restored and checked byte-identical afterwards.

POSCAR rejections were checked by hand rather than by test, per D-015: Cartesian,
`-8.0` and `1 1 1` scales raise; `2.0` scales the lattice; Selective dynamics is accepted.

## Decisions or deviations

None recorded in DECISIONS. Differences from the spec's motivating notes. None of
these is in the expected-results table, and none changes the code:

- BFO with `sigma = 1e-3` at `symprec = 3e-2` depends on the noise draw. Over 20
  seeds it gave `R3c` 4 times, `R3` 9, `Cc` 4 and `P1` 3. It gave `R3c` on all 20
  at `5e-2`. The `sigma = 2e-4` claims (`P1` with 9/6/3 at `1e-3`, `R3c` at `1e-2`)
  held on all 20 seeds.
- Marking one BFO Fe as magnetic is rejected as the spec says, but the largest
  site distance is 3.9 Å here, the Fe-Fe spacing, not 6.8 Å.
- The largest accepted site distance on the noisy structures was `0.86 * symprec`,
  not 0.99. It depends on the draw, and both are below the `2 * symprec` guard.
- BFO lattice rounded to 4 decimals gives `|R^T R - I| = 1.6e-5`, not 2e-5, and
  unchanged `p_D, p_A = 1, 2`. Zero singular values are at or below 1.2e-16.

The venv on this machine is at `pipeline v3/.venv`, not at the repository root as
README says. The README was left unchanged, since this is local setup.

## Handoff

- Completed work: TEN-02 as specified.
- Remaining work / blockers: user review and merge. Then the TEN-03 spec.
- Next concrete command or action: review the TEN-02 pull request.
- Files another session should read: `pipeline v3/dmi_pipeline/symmetry.py`,
  `pipeline v3/tests/test_symmetry.py`, `plans/ten-02-symmetry.md`.
- Last tested commit, if available: the branch head that contains this log.
- Uncommitted/unpushed work and where it exists: none after the push.
