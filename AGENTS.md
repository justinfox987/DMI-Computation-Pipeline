# Working on this spin-spiral tensor project

## Start every session

1. Read `STATUS.md`, `docs/DECISIONS.md` and the task spec in `plans/`
   (`plans/ten-NN-*.md`). For physics or pipeline work, also read
   `docs/math/heide_math_v3.md`. If the task has no spec yet, write one in
   `plans/` and get the user's approval before writing code.
2. Inspect `git status --short --branch`, the current branch and recent commits.
   Preserve existing edits. Read any more-specific repository instructions.
3. Check the task owner/branch in STATUS and the latest relevant session log.
   Reconcile this with the actual checkout; a status sheet is not evidence of code.
4. State the task scope and relevant files before editing. Create one branch
   per task from `main`, such as `ten-02-symmetry`. Never push to `main`: the
   user reviews and merges every pull request.

## Current direction

The project computes the spiralization tensor, stiffness tensor and exchange
classes from flat spin spirals, then uses them to predict magnetic properties.
It no longer fits bond-resolved DMI vectors. The code must work for any material
with one magnetic order parameter; BFO is a test material, not a special case.
The near-term goal is working calculations and a paper, so choose the simple path
that runs over machinery no current material needs.

The repository is mid-pivot, so older files can describe removed work:

- Tag `archive/bond-dmi-v3` marks the pre-pivot state at `490a4e1`.
- The campaign orchestration, the bond rows, the constrained families and
  `step1.py` are removed. Do not reintroduce them.
- Work only in `pipeline v3/`. Ignore `pipeline v4/`.
- Add `symmetry.py`, `spiral.py` and `tensors.py`. `spglib` is the one approved
  new dependency, and it is for symmetry operations only.
- Each material is one folder under `materials/` with a `seed.toml`
  (`docs/seed_file.md`). POSCAR is the main input, and the seed holds no machine
  paths.
- Keep `acceptance/` and `evidence/` as historical records. Do not relabel them
  as evidence for the new pipeline.

## Code for sustainability and simplicity

Treat every addition as a maintenance obligation. Prefer the smallest coherent
change that satisfies the requirement and preserves scientific correctness.
Optimize for fewer concepts, clear behavior and one authoritative implementation,
not merely fewer lines or a smaller-looking diff.

### Examine before adding

- **Spend reasoning tokens on understanding and simplifying the existing code.**
  Deliberately budget time for repository searches, reading implementations and
  callers, checking redundancy, and reviewing consistency. Do not spend the
  whole budget generating code and leave these checks until the end.
- Before adding a function, class, module, parser, configuration option or data
  field, search for the behavior it would provide. Search related concepts and
  call sites, not only the proposed name. Read existing tests and consumers.
- Identify the current authoritative path. Prefer reusing, correcting or
  modestly extending it over adding a parallel implementation. If a new path is
  necessary, briefly explain why the existing one cannot reasonably serve.
- Fix a problem where it originates. Avoid adding downstream adapters, fallback
  values or special cases merely to conceal an inconsistent upstream contract.

### Keep the implementation small and coherent

- Solve the present requirement. Do not add speculative extensibility, generic
  frameworks, plugin systems, new dependencies or configuration switches without
  a concrete need in the current task.
- Add an abstraction only when it removes meaningful duplication, establishes
  a useful boundary or makes the domain clearer. Avoid pass-through wrappers,
  one-use class hierarchies and chains of helpers that obscure a simple operation.
  Conversely, do not force unrelated behavior into one clever generic helper.
- Keep shared rules in one place: formulas, units, indexing conventions, parsing
  rules, defaults and acceptance criteria must not drift between copies.
  Similar-looking quantities with different meanings must remain distinct;
  for example, M_int and MW_int are not interchangeable.
- When replacing behavior, update its live callers and remove the superseded
  implementation, unused imports, stale options and contradictory tests/docs
  within the task's scope. Verify references and supported interfaces first.
  Keep required compatibility explicit and isolated; do not retain two competing
  production paths “just in case.” Preserve scientific evidence and unrelated work.
- Validate at meaningful boundaries and reuse established validation. Avoid
  duplicating the same checks at every layer, but retain checks needed to reject
  invalid scientific inputs. Missing evidence must not become a silent default.
- Prefer readable names and straightforward control flow. Explain non-obvious
  scientific conventions in comments; do not narrate obvious syntax.

### Review the whole affected path

- Before finishing, trace the change from input through computation to output.
  Check consistency across writers, readers, schemas, callers, CLI behavior,
  defaults, units, signs, indexing, tolerances, tests and documentation.
- Re-read the diff specifically for code that can be deleted, reused or combined.
  Ask whether a function already does the job, whether a new branch is necessary,
  and whether the change has introduced another source of truth.
- Keep the test suite small: aim for under 30 tests in total. Write one test per
  physics result or file-format contract, not one per validation branch, input
  variant or bug fixed. To add a test, first look for one it can replace or extend.
- Test meaningful behavior and the relevant failure modes. Reuse fixtures and
  independent reference checks; avoid tests that only repeat the implementation
  or mock away the integration being changed.
- In the handoff, briefly state what was reused or removed and justify substantial
  new abstractions or code growth. Passing tests alone does not establish that
  the design is consistent or maintainable.

## Scientific authority

- Current foundation: `docs/math/heide_math_v3.tex`, **Revision 3.1**.
- `docs/math/heide_math_v3.md` is the agent edition, with the same section and
  equation numbers. Its opening notes give the module map and the rules that must
  not drift. Change the two files together. If they disagree, the TeX wins and
  the conflict must be reported.
- Superseded for current work: `docs/math/heide_math_v2.tex` and everything in
  `docs/archive/`, including the Step 1 spec, the Perlmutter pilot guide, the old
  Perlmutter runner plan and old project records.
  Use them for history and retained Patch B detail. They must not silently
  override Revision 3.1.
- Run unconstrained flat F0 spirals at `LAMBDA = 0`. Do not reintroduce F1, F2,
  constraints, bond bases or bond rows without a recorded user decision.
- Write physical lab-vector targets without pre-unwinding, and read directions
  from OSZICAR `M_int`. Never substitute target directions for measured ones.
- Keep first-order SOC, the frozen-state trace and computed pairs at both signs
  of q. Do not add a second spin-axis rotation.
- Report the free 9-component spiralization fit and its forbidden part, not only
  the symmetry-constrained result. That check cannot see an overall sign, so the
  sign needs an external anchor.
- Mathematical equivalence, spin-model recovery, local test passes and production
  VASP validation are separate claims. State which evidence supports each result.
- Do not fabricate run metadata, hashes, convergence, uncertainties or gate passes.

## Coordinate changes

- Use one writing agent per branch/worktree. Concurrent tasks need separate
  branches/worktrees and agreed file ownership; do not share a writable checkout.
- Record owner, branch and scope before parallel work. A claim in an unpushed
  branch is not visible to another machine; publish or communicate the claim.
  STATUS is a handoff record, not a distributed lock.
- Avoid repository-wide reformatting, directory moves or framework changes
  alongside a physics correction.
- Do not erase another task's edits or rewrite shared history to resolve a conflict.
  Read the conflict and preserve the intended behavior of both changes.
- Use focused commits including relevant tests and documentation. Stage only
  the task's files/hunks; inspect the staged diff.

## Verify and leave a handoff

- Discover the current installation and test commands from the actual checkout.
  Do not assume the historical inventory's test counts still apply.
- Run checks relevant to changed behavior. Record exact commands, outcomes and
  pre-existing failures; distinguish not-run checks from passes.
- Write one session log using `docs/sessions/TEMPLATE.md`, named
  `YYYY-MM-DD_HHMMZ-agent-task.md` with a unique suffix if needed.
- Update STATUS with the next concrete action, blockers and supporting log.
  In task branches, retain other owners' entries; reconcile STATUS at integration.
- Add to CHANGELOG for meaningful code/interface/document changes.
  Add to DECISIONS only for a durable choice or an explicit supersession.
- The final response names changed files, verification and remaining work.
  Uncommitted or unpushed work must be identified as such.

## Repository boundaries

Keep code, tests, specs, small deliberate evidence and logs in Git. Keep bulk
calculation output, machine-local paths/credentials and VASP installation
assets outside the tracked source tree. Use `evidence/README.md` for run records.
Do not submit VASP jobs or contact the cluster unless the user asks for it.
