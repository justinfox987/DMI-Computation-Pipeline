# Working on this DMI project

## Start every session

1. Read `STATUS.md`, `docs/DECISIONS.md` and the applicable task spec.
2. Inspect `git status --short --branch`, the current branch and recent commits.
   Preserve existing edits. Read any more-specific repository instructions.
3. Check the task owner/branch in STATUS and the latest relevant session log.
   Reconcile this with the actual checkout; a status sheet is not evidence of code.
4. State the task scope and relevant files before editing. Use an existing task
   branch, or create a focused branch from the agreed integration base.

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
- Test meaningful behavior and the relevant failure modes. Reuse fixtures and
  independent reference checks; avoid tests that only repeat the implementation
  or mock away the integration being changed.
- In the handoff, briefly state what was reused or removed and justify substantial
  new abstractions or code growth. Passing tests alone does not establish that
  the design is consistent or maintainable.

## Scientific authority

- Current foundation: `docs/math/heide_math_v2.tex`, **Revision 2.4**.
- Current migration: `docs/dmi_step1_implementation_spec.md`.
- `docs/archive/` contains historical snapshots, including superseded frame
  assumptions. It must not silently override the current spec.
- Implement physical lab-vector targets and OSZICAR sphere readback as specified.
  Keep `M_int` geometry distinct from `MW_int` constraint checks.
- Keep first-order SOC, full-operator axis selection, canonical bond counting
  and two-sided measured rows. Do not add a second spin-axis rotation.
- Mathematical equivalence, local test passes and production VASP validation
  are separate claims. State which evidence supports each result.
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
Step 1 does not include submitting VASP jobs.
