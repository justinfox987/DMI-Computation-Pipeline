# Cleanup 1: remove dead and duplicate code without changing behavior

Status: approved by the user on 2026-11-09 ("ok, now cleanup"), from the target
list in that conversation. Implemented on `cleanup-1` from `main` at `ec3e961`.

## Rule

Nothing the pipeline computes, writes or prints may change. No physics formula,
tolerance, guard or error message changes. Tests change only where the code they
import moves, and to close a gap the fault injections expose.

## Targets

| Target | Done |
|---|---|
| `trace.py`: the CPROJ trace of Eq (4.7) is used only by tests. Move one copy into `tests/fixtures.py` as the oracle, still calling the production `assert_state_inputs`; delete the explicit-loop copy and `TraceResult` | Yes |
| `spiral.sphere`: return only what callers read (`M_int`, `lambda`, step counters); remove `printed_step` and the unused `MW_int`, precision, field, `E_p` and line-number outputs; keep every check that raises | Yes |
| `dumpio.py`: delete `read_header`. `set_dd_paw_call` stays, because CSO requires it as a header field | Yes |
| Run-tree loading in `check_tree`, `prepare_dumps` and `observables`: merge only if clearly simpler. Each is one or two lines, so only the `runs.txt` parse becomes one helper, `spiral.run_names` | Partly |
| `__main__.py`: table-driven parser. The standalone `gate` and `t3` commands duplicate what `dmi trace` runs through `finish`, and no test used them; removed with `gates.t3` and `manifest.fingerprints` | Yes |
| spglib's `DeprecationWarning` | Filtered in pytest only. Opting in to spglib's new error handling would break the declared `spglib>=2.6` floor (2.6 has no `spglib.error`) and turn its failure into an exception the command line does not catch |

Not touched, until TEN-06 has real files: the CPROJ format probing in `dumpio.py`
and the structure of the OSZICAR parser. Not merged: `manifest.check_files` and
`spiral.unchanged`, because unifying them changes error messages that two tests
match.

## Proof of preservation

1. A script runs `plan`, `prepare`, `collect`, `dumps`, `trace` and `fit` on one
   synthetic BFO tree built from the test fixtures, and stores every JSON output,
   every generated INCAR and job script, and every printed line. Two runs on
   `main` are byte-identical, so the comparison is deterministic. The branch
   output is byte-identical to `main`'s.
2. The 21 tests pass.
3. 28 fault injections from the TEN-02 to TEN-05 reviews are rerun. All are
   caught. The one new injection, removing the final-`lambda` check in
   `read_run`, was missed by the tests on `main` too; the readback test now
   covers it.
