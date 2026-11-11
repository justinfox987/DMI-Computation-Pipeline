# Agent notes for the math document

**Revision 3.2, 11 November 2026.** The mathematics lives in one file,
`heide_math_v3.tex`. Read the TeX for any physics or pipeline work. This file no
longer copies it (D-025); it holds only the module map and the rules below.
Section and equation numbers are those of the TeX.

Evidence: the equations were checked numerically on spin models and repository
fixtures. The sign correction of Section 4 rests on the VASP source and a
bookkeeping test. No VASP calculation has tested this revision. Do not describe
any result as physically validated on that basis.

## Where each part lands in the code

| Module | Implements |
| --- | --- |
| `symmetry.py` | Eqs. (7.1)–(7.3) kept operations; (7.6)–(7.7) bases; (7.9) twist count; (7.11) exchange classes (not yet used) |
| `spiral.py` | Eq. (3.1) targets; Section 3 inputs and readback; (3.2)–(3.3) phases; (8.1) and Section 8 $q$ plan |
| `trace.py` | Eqs. (4.4), (4.8) orbital matrices and trace vector, with the file-array contraction of Section 4.4 |
| `tensors.py` | Eqs. (1.3), (1.4) observables; Section 9 fits; Section 10 predictions and units |
| `gates.py` | Section 11 checks |
| `anisotropy.py` (later) | Section 13; spec in `plans/anisotropy-1.md` |

## Rules that must not drift

- Pair observable: $y_\alpha=[T_\alpha(\boldsymbol q)-T_\alpha(-\boldsymbol q)]/N_{\mathrm m}=2\,\hat{\boldsymbol e}_\alpha^{T}\mathcal D\,\boldsymbol q$. No additional factor of one-half.
- Spiralization is a pseudotensor: keep $\det(R)$ in Eq. (7.5). Stiffness has no such factor.
- SCFs run at `LAMBDA = 0`. Never replace measured `M_int` with target directions.
- `CSO.dat` and `COCC.dat` both store the ket index first. Contract them as VASP does, $\mathrm{Re}\sum\Lambda^{\rm file}\,\overline{(\mathrm{COCC}_{\uparrow\uparrow}-\mathrm{COCC}_{\downarrow\downarrow})}$. Dropping the conjugate reverses the sign of every trace, and no null test sees it.
- Keep all four CSO blocks when reading: $\Lambda_x$ and $\Lambda_y$ live in the flip blocks. The split triple from the file must be left-handed ($h<0$) on every ion.
- The design matrix of the fit must have full column rank. Three non-coplanar directions do not guarantee a determined $A$.
- Noise comes from the parity residuals, Eq. (9.9), not from fit residuals.
- Keep `M_int` and `MW_int` distinct; only `M_int` supplies directions here.
- Match the OUTCAR energy line with flexible whitespace, for example `free\s+energy\s+TOTEN`, and take the last match.
- Every command reads the VASP files again. No derived file is trusted as input.
- The electronic settings are the user's (D-019). The one rule is no tetrahedron smearing (D-022).
- Do not write unit tests that only repeat an implementation. Use the spin-model oracle of Section 6 and the layout test of Section 4.4.
