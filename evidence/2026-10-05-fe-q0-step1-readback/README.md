# Historical Fe Step 1 readback, 2026-10-05

This is a diagnostic reconstruction of the historical `reader_test_2` inputs,
not a claim that the run was designed as an F1 calculation or that its VASP
executable matches the supplied source. No VASP job was run. The full runs remain
in the local untracked `vasp files/sample-files/` tree. The generated readback
state, which contains machine-local absolute paths, is at the ignored local path
`artifacts/local/2026-10-05-fe-q0-step1-readback/state.json` (SHA-256
`af3e7b80ab14c39b2b6eb5b0389e237ad7a02f849e804c58e364d0093c3a5b28`).

## Independent reference

The reference is `vasp files/sample-files/Fe_q0_test/q0/`. Its final OSZICAR
sphere table, lines 264-266, at ionic/electronic step `(1,20)` prints, in Fe
POSCAR order:

| Ion | MW_int | M_int | MW_int norm | M_int norm |
|---|---|---|---:|---:|
| 1 | `(1.758,-0.000,0.000)` | `(2.131,-0.000,0.000)` | 1.758 | 2.131 |
| 2 | `(1.758,0.000,0.000)` | `(2.131,0.000,0.000)` | 1.758 | 2.131 |

These displayed norms, without additional precision, are stored in
[references.json](references.json). They come from the independent q0 run, not
from the lambda=1 sample. The reference INCAR requests `QSPIRAL = 0 0 0`,
`RWIGS = 1.5`, and `LAMBDA = 0`; its OUTCAR has one completed run, the final
`Iteration 1(20)`, a subsequent EDIFF reached marker, and a timing footer.

The two POSCAR files are byte identical (SHA-256
`91e11367c9d093742a9f166e0b64c22a95db4d34ce7aa51f9a7bc3e98b9665fc`):
Fe ions 1 and 2 occupy direct coordinates `(0,0,0)` and `(0.5,0.5,0.5)`.
Both OUTCARs print the same 125 reciprocal k-point rows and the same
`vasp.6.4.2 20Jul23 (build Sep 14 2026 08:43:24) complex` banner. Their common
INCAR physics settings include Fe_pv PAW, PBE, ENCUT 550 eV, NBANDS 56,
ISMEAR 0, SIGMA 0.05, EDIFF 1e-7, ALGO All, LASPH, noncollinear spin spiral,
SAXIS `(0,0,1)`, and `RWIGS = 1.5`. The supplied source sets LZEROZ true by
default for LSPIRAL; q0 omits that tag, while the lambda=1 INCAR states True.
The runs intentionally differ in q and lambda. They also differ in initial
charge (`ICHARG = 1` versus `2`), projection output (`LORBIT = 2` versus `11`),
and parallel layout (`NCORE/KPAR = 8/2` versus `16/4`). The initial charge
choice does not change the reference's observed final convergence, but matching
binary and source identity remains unverified.

Reference raw-file SHA-256: INCAR
`83bccb69162c4b00f9065b953de0ea40065e0b3be76ec09dc1b4817841c9f868`,
OUTCAR `7d58bd39bdf6509173583a197b98a607cf813bbc155d843c714aabfa6484377a`,
OSZICAR `673e5d82e7ebc845a12242b960491300e7e30ca64d2cbca1170bb74eaaca79b7`.

## Reconstruction and result

[recipe.json](recipe.json) selects F1 diagnostic, `angle_deg = -45`, q
`(0.25,0,0)`, positive signs, and Fe indices `[0,1]`. The site-2 q phase is
`+45` degrees, giving the original `+x/+x` MAGMOM and M_CONSTR vectors.
`axis = z` is diagnostic bookkeeping; the historical run did not record a
measurement-axis choice. `step1-prepare` generated
[prepared/config.json](prepared/config.json) and
[prepared/INCAR.step1](prepared/INCAR.step1). Its config uses `T/F` logical
tokens. Unmodified `step1-read` against the historical INCAR stops at
`Run INCAR LNONCOLLINEAR differs from requested input` because the existing
comparison requires identical logical token spellings.

[historical-config.json](historical-config.json) is a copy of the prepared
config with only four logical tag values changed to the original INCAR's
`True/False` spellings: LNONCOLLINEAR, LSORBIT, LSPIRAL, and LZEROZ. It is the
config used for the full CLI readback. No target, coefficient, tolerance, code,
or original VASP file was changed. The CLI wrote the ignored `state.json` and
returned exit code 1 for a physical gate failure:

| Check | Result |
|---|---|
| Input/config binding, final OUTCAR/OSZICAR association | PASS, final step `(1,32)` |
| M_int full geometry and transverse phase | PASS, 0.83693 degrees per ion, limit 1 degree |
| M_int/MW_int mutual direction | PASS, under 1 degree |
| Absolute MW_int alignment | FAIL, 1.39101 degrees per ion, limit 1 degree |
| M_int reference magnitude drift | FAIL, 6.01788% per ion, limit 5% |
| MW_int reference magnitude drift | PASS, 3.10206% per ion, limit 5% |
| Printed penalty versus MW_int at displayed precision | PASS |
| Physical printed penalty | FAIL, 0.0039272 eV, limit 0.001 eV |
| Signed factor-two field versus MW_int | PASS at displayed precision |
| Field/penalty same-update numerical identity | UNAVAILABLE as an update check; displayed intervals disjoint, minimum gap 2.55506125e-7 eV at matched lambda 1 |

The supplied VASP source audit in
[the field/penalty session](../../docs/sessions/2026-09-30_1933Z-agent-step1-field-penalty-source-audit.md)
shows a cached penalty followed by a moment refresh before final fields on the
inspected path. The exact GPU executable's source/build identity is unavailable,
so this timing explanation does not authenticate this run or exempt other CGA
calculations. The failed realization gate prevents using this state as an
accepted parent or paired Step 1 row.
