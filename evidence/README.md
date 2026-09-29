# Scientific evidence

Keep one small directory per deliberately retained validation record, named
with a date and descriptive run/test ID. No production runs are included yet.

A record should state:

- What was tested, the expected result and the actual result.
- Exact source commit and executable identity/hash when known.
- Material/input identity, relevant tags, q, family, parity, parent and units.
- Small necessary input/readback files, or clearly labeled excerpts.
- Raw-data location and checksums sufficient to reconnect to the full run.
- Which gate passed/failed/was not evaluated, and the tolerance used.

Do not present an excerpt as a complete convergence record. Unknown identities
remain unknown. Local unit-test output and production VASP evidence must be
labeled separately.

Keep bulk run directories and large electronic dumps on appropriate external
storage, with references here. Git tracks the small reproducibility record,
not every restart file. Test fixtures belong with the code's tests.

OUTCAR/OSZICAR are not globally ignored: intentionally small evidence or
fixtures may be committed. Bulk run locations are ignored instead.
