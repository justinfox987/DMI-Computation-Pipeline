# From Heide's Force Theorem to Magnetic Tensors

Computing spiralization, stiffness and exchange from paired, SOC-free spin spirals.

**Revision 3.0, 2 November 2026.** Markdown edition for coding agents.

## Agent notes

- This file carries the same content and numbering as `heide_math_v3.tex`, so a reference such as Eq. (1.3) means the same thing in both. If they ever disagree, the TeX source wins; report the conflict rather than choosing silently.
- This revision replaces the bond-vector target of Revision 2.4. It keeps the generalized-Bloch states, Patch B frozen-state trace and lab-frame moment readback. It removes the constrained families F1 and F2, the bond basis and the paired bond rows.
- Evidence: the new equations were checked numerically on spin models and repository fixtures. No VASP calculation has yet tested this revision. Do not describe any result as physically validated on that basis.

### Where each part lands in the code

| Module | Implements |
| --- | --- |
| `symmetry.py` | Eqs. (7.1)–(7.3) kept operations; (7.6)–(7.7) bases; (7.9) twist count; (7.11) exchange classes |
| `spiral.py` | Eq. (3.1) targets; Section 3 inputs and readback; (3.2)–(3.3) phases; (8.1) and Section 8 $q$ plan and rank conditions |
| `trace.py` | Eqs. (4.4), (4.7), (4.8) orbital matrices and trace vector |
| `tensors.py` | Eqs. (1.3), (1.4) observables; Section 9 fits; Section 10 predictions and units |
| `gates.py` | Section 11 checks |

### Rules that must not drift

- Pair observable: $y_\alpha=[T_\alpha(\boldsymbol q)-T_\alpha(-\boldsymbol q)]/N_{\mathrm m}=2\,\hat{\boldsymbol e}_\alpha^{T}\mathcal D\,\boldsymbol q$. No additional factor of one-half.
- Spiralization is a pseudotensor: keep $\det(R)$ in Eq. (7.5). Stiffness has no such factor.
- SCFs run at `LAMBDA = 0`. Never replace measured `M_int` with target directions.
- `COCC[i,j]` is $\rho[j,i]$: contract elementwise, not with a matrix trace.
- Keep all four CSO blocks when reading: $\Lambda_x$ and $\Lambda_y$ live in the flip blocks.
- Use both rank conditions of Section 8.2. Three non-coplanar directions do not guarantee a determined $A$.
- Keep `M_int` and `MW_int` distinct; only `M_int` supplies directions here.
- Match the OUTCAR energy line with flexible whitespace, for example `free\s+energy\s+TOTEN`, and take the last match. Spacing in this line is not a safe literal.
- Do not write unit tests that only repeat an implementation. Use the spin-model oracle of Section 6.

## Abstract

The calculation has four parts. First, VASP prepares an unconstrained SOC-free flat spin spiral for a chosen magnetic pattern. Second, a frozen-state PAW trace gives its first-order spin–orbit energy, as a vector with one component per Cartesian axis. Third, symmetry fixes which tensor components are allowed and which $q$ points are needed. Fourth, small linear fits turn traces and total energies into the spiralization tensor, the stiffness tensor and exchange classes.

This document derives what the code needs for those steps and nothing more. The tensors are long-wavelength sums of the bond interactions, so they avoid the bond-resolution limit of flat spirals. They then give predictions such as the spiral period, spin plane and texture class.

## 1. What the calculation measures

We consider a magnet with one slowly varying order parameter: a ferromagnet, or a collinear pattern of site signs $\varepsilon_a=\pm1$ in the magnetic primitive cell. A flat spiral twists that pattern with wavevector $\boldsymbol q$ about a spin-rotation axis $\hat{\boldsymbol n}$:

$$
\hat{\boldsymbol{S}}_a(\boldsymbol{r})=\varepsilon_a
 \bigl[\hat{\boldsymbol{e}}_1\cos(\boldsymbol q\cdot\boldsymbol{r})
 +\hat{\boldsymbol{e}}_2\sin(\boldsymbol q\cdot\boldsymbol{r})\bigr],
 \qquad \hat{\boldsymbol{e}}_1\times\hat{\boldsymbol{e}}_2=\hat{\boldsymbol n}. \tag{1.1}
$$

For long wavelengths, the energy per magnetic site relative to $\boldsymbol q=0$ is

$$
\boxed{e(\boldsymbol q,\hat{\boldsymbol n})=\boldsymbol q^{T}A\,\boldsymbol q+\hat{\boldsymbol n}^{T}\mathcal D\,\boldsymbol q+O(q^3).} \tag{1.2}
$$

$A$ is the symmetric *stiffness tensor*; it comes from SOC-free exchange. $\mathcal D$ is the $3\times3$ *spiralization tensor*; it comes from SOC at first order. Anisotropy is second order in SOC and is treated separately in Section 10.

Two measured quantities isolate these tensors. Let $T_\alpha(\boldsymbol q)$ be the first-order SOC energy per calculation cell with the operator selecting Cartesian axis $\alpha$, and let $E(\boldsymbol q)$ be the SOC-free total energy per cell. Then

$$
y_\alpha(\boldsymbol q)=\frac{T_\alpha(\boldsymbol q)-T_\alpha(-\boldsymbol q)}{N_{\mathrm m}}
 =2\,\hat{\boldsymbol{e}}_\alpha^{\,T}\mathcal D\,\boldsymbol q+O(q^3), \tag{1.3}
$$

$$
g(\boldsymbol q)=\frac{E(\boldsymbol q)+E(-\boldsymbol q)-2E(0)}{2N_{\mathrm m}}
 =\boldsymbol q^{T}A\,\boldsymbol q+O(q^4). \tag{1.4}
$$

$N_{\mathrm m}$ is the number of magnetic sites in the calculation cell. Note the factor of two in Eq. (1.3). It is the same paired observable as Revision 2.4, with *no additional factor of one-half*.

The same energies at larger $q$ also determine exchange classes $J_c$ (Section 7.6). One least-squares routine handles all three quantities; only the symmetry rule and the row differ.

Throughout, $\boldsymbol q_{\rm frac}$ denotes reciprocal fractional coordinates and $\boldsymbol{r}_{\rm frac}$ direct fractional coordinates: $\boldsymbol q\cdot\boldsymbol{r}=2\pi\boldsymbol q_{\rm frac}\cdot\boldsymbol{r}_{\rm frac}$. Without a subscript, $\boldsymbol q$ is Cartesian in Å$^{-1}$. Energies are per magnetic site unless stated. $\mathcal D$ then has units of eV Å and $A$ of eV Å$^2$.

## 2. The DFT state and the first-order SOC energy

### 2.1 What is frozen

The electronic calculation follows the first-order spin-spiral method of Heide, Bihlmayer and Blügel [1]. For each spiral, VASP solves the noncollinear SOC-free Kohn–Sham problem,

$$
H^{(0)}_{\rm KS}[\rho,\boldsymbol{m}]\,\Psi^{(0)}_{n\boldsymbol k}
 =\varepsilon^{(0)}_{n\boldsymbol k}\Psi^{(0)}_{n\boldsymbol k}. \tag{2.1}
$$

The first-order SOC insertion is

$$
\Delta E^{(1)}=
 \sum_{n\boldsymbol k}w_{\boldsymbol k}f^{(0)}_{n\boldsymbol k}
 \langle\Psi^{(0)}_{n\boldsymbol k}|H_{\rm SOC}|\Psi^{(0)}_{n\boldsymbol k}\rangle. \tag{2.2}
$$

This is the derivative of the stationary electronic energy with respect to a small SOC coupling. Stationarity is why it can be evaluated on the unperturbed orbitals and occupations. It is an SOC expectation, not VASP's full `TOTEN`, so the two kinds of energy are never added together.

### 2.2 Why a spin spiral fits in the chemical cell

Without SOC, the electronic functional is invariant under a common spin rotation, so a translation can be accompanied by a spin rotation. VASP's `LNONCOLLINEAR = T`, `LSPIRAL = T` representation uses

$$
\Psi_{n\boldsymbol k}(\boldsymbol{r})=
 \begin{pmatrix}
 e^{\mathrm{i}(\boldsymbol k-\boldsymbol q/2)\cdot\boldsymbol{r}}\,u_{n\boldsymbol k\uparrow}(\boldsymbol{r})\\
 e^{\mathrm{i}(\boldsymbol k+\boldsymbol q/2)\cdot\boldsymbol{r}}\,u_{n\boldsymbol k\downarrow}(\boldsymbol{r})
 \end{pmatrix},
 \qquad u(\boldsymbol{r}+\boldsymbol{R})=u(\boldsymbol{r}). \tag{2.3}
$$

The transverse magnetization rotates by $\boldsymbol q\cdot\boldsymbol{R}$ between cells. This generalized Bloch construction avoids a supercell for every `QSPIRAL` [5]. SOC breaks this freedom, so the spiral is prepared with `LSORBIT = F` and SOC is inserted afterward.

### 2.3 Why the SCF stays unconstrained

Each sublattice phase may differ from the rigid value $\boldsymbol q\cdot\boldsymbol{\tau}_a$ by a small amount $\delta_a$. Let $\xi$ scale the SOC. Then

$$
E(\xi,\boldsymbol{\delta})=E_0(\boldsymbol{\delta})+\xi\,T(\boldsymbol{\delta})+O(\xi^2). \tag{2.4}
$$

Minimizing over $\boldsymbol{\delta}$ changes the energy only at $O(\xi^2)$, because $E_0$ is stationary at its own minimum $\boldsymbol{\delta}^*$. The complete first-order result is therefore $T(\boldsymbol{\delta}^*)$, evaluated on the *relaxed* SOC-free state. A rigid state generally has the wrong $E_0$ at $O(q^2)$ and, since $\boldsymbol{\delta}^*\propto\boldsymbol q$ when allowed, the wrong $T$ at $O(q)$.

We therefore run with `LAMBDA = 0` and let the SCF find the phases. Symmetry decides when the relaxation can occur (Section 7.5). A flat spiral of one order parameter is already a stationary SOC-free state, so the constrained-family machinery of Revision 2.4 is not needed.

## 3. Preparing and reading one spiral

### 3.1 The target

Use `SAXIS = 0 0 1`. Lab frame means these fixed Cartesian spin axes, independent of $\boldsymbol q$. In the production states the rotation axis is always $\hat{\boldsymbol{z}}$. For magnetic site $a$ at direct position $\boldsymbol{\tau}_{a}$,

$$
\boxed{\hat{\boldsymbol{S}}_a^0(\boldsymbol q)=
 \varepsilon_a\bigl(\cos\phi_a,\ \sin\phi_a,\ 0\bigr),
 \qquad \phi_a=2\pi\boldsymbol q_{\rm frac}\cdot\boldsymbol{\tau}_{a,\rm frac}.} \tag{3.1}
$$

This single formula covers every site count. The partner is the same formula at $-\boldsymbol q$, and the $q=0$ reference is the same formula at $\boldsymbol q=0$.

### 3.2 VASP inputs

| Tag | Value and reason |
| --- | --- |
| `LNONCOLLINEAR`, `LSPIRAL` | `T`, also for the $q=0$ reference. |
| `LSORBIT` | `F`. SOC enters only through the trace. |
| `QSPIRAL` | $\boldsymbol q_{\rm frac}$, in reciprocal lattice units. |
| `LZEROZ`, `SAXIS` | `T` and `0 0 1`: flat spiral about $z$. |
| `ISYM` | $-1$. VASP symmetry does not account for the spiral [6]. |
| `I_CONSTRAINED_M`, `LAMBDA` | $1$ and $0$. This gives sphere moments with no penalty. |
| `RWIGS` | One explicit radius per species. |
| `ENCUT`, `ENINI` | `ENCUT` about 100 eV above `ENINI`, as the wiki advises. |
| `MAGMOM` | $m_a\hat{\boldsymbol{S}}_a^0$, with seed magnitude $m_a$. |
| `M_CONSTR` | $\hat{\boldsymbol{S}}_a^0$. It has no effect at `LAMBDA = 0`. |

**Do not pre-unwind `MAGMOM`.** VASP's `COUNTER_SPIRAL` applies the internal rotation $R_z(-\phi_a)$ itself [9]. Keep the $k$ mesh, cutoffs, smearing and spheres identical across all $q$ of one material.

### 3.3 Reading the state

Read the final complete `M_int` block of OSZICAR, in POSCAR ion order. The vectors are lab components, and they are the only source of site directions. Let $M_a(\boldsymbol q)$ be the length of that vector on site $a$. In-plane directions are conveniently complex numbers:

$$
s_a=\frac{M^{\rm int}_{a,x}+\mathrm{i} M^{\rm int}_{a,y}}{M_a},
 \qquad u_a=\varepsilon_ae^{\mathrm{i}\phi_a}. \tag{3.2}
$$

SOC-free energies do not depend on a common rotation about $z$, so remove the best common angle before comparing with the target:

$$
\theta=\arg\sum_a u_a^*s_a,\qquad
 \delta_a=\arg\bigl(u_a^*s_ae^{-\mathrm{i}\theta}\bigr). \tag{3.3}
$$

$\delta_a$ is the realized phase relaxation of site $a$. It keeps the sign of the moment: a reversed site gives $\delta_a\simeq180^\circ$. In the historical $\lambda=0$ bcc Fe run, sites seeded along $+x$ reached a $45.34^\circ$ difference against the $45^\circ$ F0 value [9]. This shows that unconstrained phases do move, and sets a first estimate of their convergence error.

The total energy is the final OUTCAR `free  energy   TOTEN`, which prints more digits than OSZICAR. With $\lambda=0$ it contains no penalty energy.

## 4. From the PAW expression to the trace vector

### 4.1 Why the all-electron on-site matrix appears

Define the projector coefficients and all-electron on-site SOC matrix by

$$
c^\mu_{i,n\boldsymbol k s}=
 \langle\tilde p_i^\mu|\tilde\Psi_{n\boldsymbol k s}\rangle,\qquad
 C^{\mu,ss'}_{ij}=
 \langle\phi_i^\mu|H_{\rm SOC}^{ss'}|\phi_j^\mu\rangle. \tag{4.1}
$$

Here $\mu$ labels an atom and $i,j$ its partial-wave channels. The PAW expectation of a local operator is a smooth term plus an all-electron-minus-pseudo on-site correction. Within the one-center expansion the smooth part inside a sphere cancels its pseudo subtraction. Neglecting SOC outside the spheres leaves the all-electron on-site matrix, which is VASP's approximation [7]. The validated `CSO` dump supplies $C$ directly, so no radial integral is coded.

### 4.2 Split the operator into three orbital matrices

The SOC operator is linear in the Pauli matrices. On each atom,

$$
C=\sum_{\alpha=x,y,z}\sigma_\alpha\otimes\Lambda_\alpha, \tag{4.2}
$$

where each $\Lambda_\alpha$ is an orbital matrix. For the atomic form, $\Lambda_\alpha=\xi L_\alpha$. Reading off the four spin blocks gives

$$
\begin{pmatrix}
 C_{\uparrow\uparrow}&C_{\uparrow\downarrow}\\
 C_{\downarrow\uparrow}&C_{\downarrow\downarrow}
 \end{pmatrix}=
 \begin{pmatrix}
 \Lambda_z&\Lambda_x-\mathrm{i}\Lambda_y\\
 \Lambda_x+\mathrm{i}\Lambda_y&-\Lambda_z
 \end{pmatrix}, \tag{4.3}
$$

and therefore

$$
\boxed{\Lambda_x=\tfrac12\bigl(C_{\uparrow\downarrow}+C_{\downarrow\uparrow}\bigr),
 \quad
 \Lambda_y=\tfrac{1}{2\mathrm{i}}\bigl(C_{\downarrow\uparrow}-C_{\uparrow\downarrow}\bigr),
 \quad
 \Lambda_z=\tfrac12\bigl(C_{\uparrow\uparrow}-C_{\downarrow\downarrow}\bigr).} \tag{4.4}
$$

One `CSO` dump at `SAXIS = 0 0 1` thus supplies all three. Keep all four blocks when reading it: the $x$ and $y$ information lives in the flip blocks. The block order in the file is a stored convention, which T3 checks.

### 4.3 Selecting the rotation axis

The production state rotates about $z$. Let $U$ be a spin rotation with $U\sigma_zU^\dagger=\hat{\boldsymbol n}\cdot\boldsymbol{\sigma}$. Because the SOC-free energy is unchanged by $U$, the state $U|\Psi\rangle$ is the same spiral with rotation axis $\hat{\boldsymbol n}$. Its SOC expectation is

$$
\langle U\Psi|C|U\Psi\rangle=\langle\Psi|U^\dagger CU|\Psi\rangle,
 \qquad
 U^\dagger CU=\sigma_z\otimes(\hat{\boldsymbol n}\cdot\boldsymbol{\Lambda})+\text{(flip terms)}. \tag{4.5}
$$

From Eq. (2.3), a translated projection of spin $s=\pm1$ acquires $e^{\mathrm{i}(\boldsymbol k-s\boldsymbol q/2)\cdot\boldsymbol{R}}$. Diagonal blocks have no remaining phase, while flip blocks carry $e^{\pm\mathrm{i}\boldsymbol q\cdot\boldsymbol{R}}$. Their lattice average vanishes:

$$
\frac{1}{N_R}\sum_{\boldsymbol{R}}e^{\pm\mathrm{i}\boldsymbol q\cdot\boldsymbol{R}}=0,
 \qquad \boldsymbol q\notin\{\text{reciprocal lattice vectors}\}. \tag{4.6}
$$

The flip *contribution* vanishes, not the stored flip blocks. Only $\sigma_z\otimes(\hat{\boldsymbol n}\cdot\boldsymbol{\Lambda})$ remains, which is linear in $\hat{\boldsymbol n}$.

### 4.4 The trace vector

One state therefore gives a whole vector, with no second SCF and no rotation of the moments:

$$
\boxed{T(\hat{\boldsymbol n})=\hat{\boldsymbol n}\cdot\boldsymbol{T},\qquad
 T_\alpha=\sum_{\mu n\boldsymbol k}w_{\boldsymbol k} f^{(0)}_{n\boldsymbol k}
 \sum_{s=\pm1}s\,[\boldsymbol{c}^\mu_{n\boldsymbol k s}]^\dagger\Lambda_\alpha^\mu
 \,\boldsymbol{c}^\mu_{n\boldsymbol k s}.} \tag{4.7}
$$

Summing over occupied states first gives the density-matrix form,

$$
\rho^{\mu s}_{ij}=
 \sum_{n\boldsymbol k}w_{\boldsymbol k}f^{(0)}_{n\boldsymbol k}
 c^\mu_{i,n\boldsymbol k s}c^{\mu *}_{j,n\boldsymbol k s},\qquad
 \boxed{T_\alpha=\sum_\mu
 \operatorname{Tr}\bigl[\Lambda_\alpha^\mu
 \bigl(\rho^{\mu\uparrow}-\rho^{\mu\downarrow}\bigr)\bigr].} \tag{4.8}
$$

This needs only the on-site `COCC` blocks, not the full `CPROJ` arrays, which is a large storage saving. The stored convention matters: $\texttt{COCC}[i,j]=\rho[j,i]$. The implementation therefore contracts `sum(Lambda * (COCC_uu - COCC_dd))` elementwise, not `trace(Lambda @ ...)`, which inserts the wrong transpose. A wrong transpose can still give a real number, so the imaginary-part gate cannot replace this check.

The per-atom terms of Eq. (4.8) are retained. They are additive, so they later give the element-resolved origin of $\mathcal D$.

Equation (4.7) equals the rotated-operator trace of Revision 2.4, and the two agreed to $10^{-14}$ on repository fixtures for $x$, $y$, $z$ and generic axes. It removes the Euler conventions and $U$ matrices from production.

### 4.5 Parity and the null at $q=0$

Take a flat spiral with its common phase removed. A spin-only $180^\circ$ rotation about the in-plane $x$ axis sends $\phi\mapsto-\phi$, so it maps the state at $\boldsymbol q$ onto the state at $-\boldsymbol q$. It also leaves the SOC-free energy unchanged and changes $\sigma_z$ to $-\sigma_z$. Therefore, for every axis $\alpha$,

$$
T_\alpha(-\boldsymbol q)=-T_\alpha(\boldsymbol q),\qquad E(-\boldsymbol q)=E(\boldsymbol q). \tag{4.9}
$$

Equivalently, $(\boldsymbol q,\hat{\boldsymbol n})$ and $(-\boldsymbol q,-\hat{\boldsymbol n})$ describe the same spiral.

At $\boldsymbol q=0$ the state is collinear, and the same rotation about the collinear axis maps it onto itself. Therefore $T_\alpha(0)=0$ for all three axes. This also shows why $T$ contains no anisotropy.

These are exact statements about ideal states. Two independent SCFs may still differ through their branch, occupations or convergence, so production computes both signs and tests Eq. (4.9) instead of assuming it.

## 5. Which VASP run supplies each quantity

The operator is a property of the material. The projections and occupations belong to one state. This separation is the central Patch B input rule [10].

| Run | Object and relevant condition |
| --- | --- |
| `dump_C` | Full `CSO` with SOC on and `LSPIRAL = F`, from a converged SOC-free in-plane reference. One per material. |
| Genuine $x$, $y$ `dump_C` | `CSO` at `SAXIS` along $x$ and $y$. Used only for check T3, once per build. |
| Spiral SCF | SOC-free state at $\pm\boldsymbol q$ and at $\boldsymbol q=0$. Supplies $E$ and `M_int`. |
| `dump_P` | `COCC` from one SOC-free `PRE_LOOP` capture, after `PROALL` and before orbital updates. Add `CPROJ` and `FERWE` on the first state of each material for check M1. |
| Exchange SCF | SOC-free state on a coarse $q$ grid. No dump, no patch. |
| Anisotropy run | Standard SOC static run at $q=0$. No patch. |

A dump stage is not a substitute for a converged parent SCF. A common `CSO` is an approximation across states, because its radial factors depend on the potential. This is expected to be small for small $q$, and the supercell anchor in Section 11 tests it.

## 6. What the tensors mean in a spin model

The DFT quantities do not need a spin model. The model below gives the tensors their meaning, and it is the oracle for the code tests.

Use the Hamiltonian of Revision 2.4, with each undirected bond $b$ counted once:

$$
H=\sum_b\bigl[-J_b\,\hat{\boldsymbol{S}}_i\cdot\hat{\boldsymbol{S}}_j
 +\boldsymbol{d}_b\cdot(\hat{\boldsymbol{S}}_i\times\hat{\boldsymbol{S}}_j)\bigr]. \tag{6.1}
$$

A bond runs from site $a$ in the home cell to site $a'$ at displacement $\boldsymbol{r}_b$. Write $\varepsilon_b=\varepsilon_a\varepsilon_{a'}$. On the flat spiral of Eq. (1.1), the two ends differ in phase by $\boldsymbol q\cdot\boldsymbol{r}_b$, so

$$
g(\boldsymbol q)=\frac{1}{N_{\mathrm m}}\sum_b\varepsilon_bJ_b\bigl[1-\cos(\boldsymbol q\cdot\boldsymbol{r}_b)\bigr],
 \qquad
 y_\alpha(\boldsymbol q)=\frac{2}{N_{\mathrm m}}\sum_b\varepsilon_b\,d_{b,\alpha}\sin(\boldsymbol q\cdot\boldsymbol{r}_b). \tag{6.2}
$$

Expanding at small $q$ and comparing with Eqs. (1.3) and (1.4) gives

$$
\boxed{\mathcal D=\frac{1}{N_{\mathrm m}}\sum_b\varepsilon_b\,\boldsymbol{d}_b\,\boldsymbol{r}_b^{\,T},
 \qquad
 A=\frac{1}{2N_{\mathrm m}}\sum_b\varepsilon_bJ_b\,\boldsymbol{r}_b\,\boldsymbol{r}_b^{\,T}.} \tag{6.3}
$$

Reversing a bond reverses both $\boldsymbol{r}_b$ and $\boldsymbol{d}_b$, so each term is independent of the chosen orientation. Equation (6.3) shows why this pivot works. A flat spiral cannot separate two bonds with the same displacement class, but it does not need to: the tensors are exactly the sums it can measure.

**A normalization check.** Take a chain with one site per cell, spacing $a$, one bond per site, exchange $J$ and $\boldsymbol{d}=d\,\hat{\boldsymbol{z}}$. The only nonzero tensor entries for this chain are $\mathcal D_{zx}=da$ and $A_{xx}=Ja^2/2$. Equation (6.2) gives $y_z=2d\sin(qa)\simeq2\mathcal D_{zx}q$ and $g=J(1-\cos qa)\simeq A_{xx}q^2$, as required.

## 7. Symmetry

Symmetry is used three ways: to count parameters before any VASP run, to choose informative $q$ directions, and to test the result. Only the crystal structure and the signs $\varepsilon_a$ are needed.

### 7.1 Operations in Cartesian form

`spglib` [8] returns operations $(W_g,\boldsymbol{t}_g)$ acting on direct fractional coordinates, $\boldsymbol{x}\mapsto W_g\boldsymbol{x}+\boldsymbol{t}_g$. Let the columns of $L$ be the lattice vectors, so that $L$ is the transpose of the POSCAR matrix. Then

$$
\boxed{R_g=LW_gL^{-1}.} \tag{7.1}
$$

The tensors use only $R_g$. The translation $\boldsymbol{t}_g$ matters for the site permutation $\pi_g$, defined by

$$
W_g\boldsymbol{\tau}_{a}+\boldsymbol{t}_g\equiv\boldsymbol{\tau}_{\pi_g(a)}
 \quad(\text{modulo lattice vectors}), \tag{7.2}
$$

with positions in fractional coordinates. It maps magnetic sites to magnetic sites.

### 7.2 Which operations apply

An operation is kept if it maps the sign pattern to itself or to its overall reverse. That is, there must be one sign $\eta_g=\pm1$ with

$$
\boxed{\varepsilon_{\pi_g(a)}=\eta_g\,\varepsilon_a\quad\text{for every }a.} \tag{7.3}
$$

Call the kept set $G$. If this test fails, the operation connects two different magnetic patterns and says nothing about the coefficients of this one. Magnetic space groups are not needed. They describe one fixed spin orientation, while $\mathcal D$ and $A$ describe the energy for all orientations of the pattern.

### 7.3 The transformation rule

Apply a kept operation to the crystal and the spiral together. The crystal is unchanged, positions and $\boldsymbol q$ are polar, and spin is axial:

$$
\boldsymbol q\mapsto R\boldsymbol q,\qquad
 \hat{\boldsymbol{S}}\mapsto\det(R)\,R\,\hat{\boldsymbol{S}},\qquad
 \hat{\boldsymbol n}\mapsto\det(R)\,R\,\hat{\boldsymbol n}. \tag{7.4}
$$

The last follows because $\hat{\boldsymbol n}$ is a cross product of two spins. If $\eta_g=-1$, every spin also reverses. That shifts the spiral phase by $\pi$ and leaves $\hat{\boldsymbol n}$ and the energy unchanged, which is why sublattice-exchanging operations still constrain the tensors. Hence $e(R\boldsymbol q,\det(R)R\hat{\boldsymbol n})=e(\boldsymbol q,\hat{\boldsymbol n})$. Since each operation's inverse is also kept, Eq. (1.2) gives

$$
\boxed{\mathcal D=\det(R)\,R\,\mathcal D\,R^{T},\qquad A=A^T=R\,A\,R^{T}\qquad\text{for all }g\in G.} \tag{7.5}
$$

Without the $\det(R)$ the rule is wrong for every improper operation. If inversion is kept, then $\mathcal D=-\mathcal D$, so $\mathcal D=0$.

### 7.4 Basis by group average

Averaging over the group projects any matrix onto the allowed form:

$$
\boxed{\mathcal P_{\mathcal D}[M]=\frac{1}{|G|}\sum_{g\in G}\det(R_g)\,R_gMR_g^{T},
 \qquad
 \mathcal P_{A}[M]=\frac{1}{|G|}\sum_{g\in G}R_gMR_g^{T}.} \tag{7.6}
$$

Apply $\mathcal P_{\mathcal D}$ to the nine unit matrices, and $\mathcal P_{A}$ to the six symmetric unit matrices. A singular-value decomposition of the results gives orthonormal bases, so that

$$
\mathcal D=\sum_{\ell=1}^{p_{\mathcal D}}d_\ell B_\ell,\qquad
 A=\sum_{\ell=1}^{p_A}a_\ell C_\ell. \tag{7.7}
$$

The rank of each set is the number of independent parameters, $p_{\mathcal D}$ or $p_A$. The same projector also gives the forbidden part of a measured tensor in Section 9.

These results are useful regression tests. In the table, $\hat{\boldsymbol{z}}$ is the principal axis, $[\hat{\boldsymbol{z}}]_\times$ is the matrix of $\boldsymbol{v}\mapsto\hat{\boldsymbol{z}}\times\boldsymbol{v}$, and in-plane stiffness is $A_\perp$ with axial stiffness $A_\parallel$.

| Point group | $\mathcal D$ | $A$ | $p_{\mathcal D},p_A$ | Texture class |
| --- | --- | --- | --- | --- |
| Inversion kept | $0$ | depends on the group | $0,\ge1$ | None |
| $23$ | $D\,I$ | $A\,I$ | $1,1$ | Bloch |
| $\bar43m$ | $0$ | $A\,I$ | $0,1$ | None |
| $3m$, $4mm$, $6mm$ | $D[\hat{\boldsymbol{z}}]_\times$ | $\mathrm{diag}(A_\perp,A_\perp,A_\parallel)$ | $1,2$ | Néel |
| $622$ | $\mathrm{diag}(D_\perp,D_\perp,D_\parallel)$ | $\mathrm{diag}(A_\perp,A_\perp,A_\parallel)$ | $2,2$ | Bloch |
| $\bar42m$, 2-fold axes on $x,y$ | $D\,\mathrm{diag}(1,-1,0)$ | $\mathrm{diag}(A_\perp,A_\perp,A_\parallel)$ | $1,2$ | Antiskyrmion |

### 7.5 Intracell twist: when rigid spirals fail

Write the relaxed phases as $\phi_a=\boldsymbol q\cdot\boldsymbol{\tau}_a+\delta_a(\boldsymbol q)$. For small $q$, $\delta_a=\boldsymbol{\eta}_a\cdot\boldsymbol q$, with one vector $\boldsymbol{\eta}_a$ per magnetic site. A common shift of all $\boldsymbol{\eta}_a$ only moves the spiral's origin, so set $\sum_a\boldsymbol{\eta}_a=0$.

In the SOC-free state a spatial operation moves sites but not spins. It maps the relaxed spiral at $\boldsymbol q$ to the relaxed spiral at $R\boldsymbol q$, with site $a$ becoming site $\pi(a)$. This requires $\boldsymbol{\eta}_{\pi(a)}=R\boldsymbol{\eta}_a+\boldsymbol{s}_g$ for some common $\boldsymbol{s}_g$. Summing over $a$ gives $\boldsymbol{s}_g=0$, so

$$
\boldsymbol{\eta}_{\pi_g(a)}=R_g\boldsymbol{\eta}_a\quad\text{for all }g\in G,\qquad
 \sum_a\boldsymbol{\eta}_a=0. \tag{7.8}
$$

Collect the $\boldsymbol{\eta}_a$ into one vector of length $3N_{\mathrm m}$. Let $\mathsf G_g$ be the matrix that places block $R_g$ at row $\pi_g(a)$ and column $a$, and let $\mathsf Q$ remove the common shift. The number of allowed twist parameters is

$$
\boxed{n_{\rm twist}=\operatorname{rank}\Bigl[
 \frac{1}{|G|}\sum_{g\in G}\mathsf G_g\,\mathsf Q\Bigr],
 \qquad
 \mathsf Q=I-\frac{1}{N_{\mathrm m}}\boldsymbol{1}\boldsymbol{1}^{T}\otimes I_3.} \tag{7.9}
$$

If $n_{\rm twist}=0$, rigid and relaxed spirals agree at first order in $q$. If $n_{\rm twist}>0$, the rigid spiral is biased. An FeGe-like toy model with $n_{\rm twist}=1$ shifted $A$ by $7\%$ and $\mathcal D$ by $35\%$; a BFO-like model with $n_{\rm twist}=0$ showed no change with independent $J$ on every bond orbit. The FeGe numbers come from arbitrary model couplings and show only the possible size of the effect. A count of one for B20 agrees with the single twist function of the published FeGe analysis [4].

**A twist check.** A dimerized antiferromagnetic chain with period $a$, bond lengths $x$ and $a-x$, and couplings $J_1$ and $J_2$ has

$$
A_{\rm rigid}=\frac{|J_1|x^2+|J_2|(a-x)^2}{4},
 \qquad
 A_{\rm relaxed}=\frac{a^2}{4}\,\frac{|J_1J_2|}{|J_1|+|J_2|}. \tag{7.10}
$$

The relaxed form is the series-spring result. Rigid and relaxed agree only when the two bond phases are already balanced, at $|J_1|x=|J_2|(a-x)$.

### 7.6 Exchange classes

For exchange, the data determine one coupling per class of equivalent displacements. List the bonds from all site pairs and cell translations within a cutoff $R_{\max}$, counting each undirected bond once. Two bonds belong to the same class $c$ if they have equal $\varepsilon_b$ and $\boldsymbol{r}'=\pm R_g\boldsymbol{r}$ for some $g\in G$. Equation (6.2) then becomes linear in the class couplings:

$$
\boxed{g(\boldsymbol q)=\sum_cJ_c\,\Phi_c(\boldsymbol q),\qquad
 \Phi_c(\boldsymbol q)=\frac{1}{N_{\mathrm m}}\sum_{b\in c}\varepsilon_b
 \bigl[1-\cos(\boldsymbol q\cdot\boldsymbol{r}_b)\bigr].} \tag{7.11}
$$

Bonds that share a displacement class merge into one effective $J_c$, in keeping with the flat-spiral limit. Use the true Cartesian $\boldsymbol q$ in the row, not $\boldsymbol q$ reduced to the first zone: for sites inside the cell, $\boldsymbol q$ and $\boldsymbol q+\boldsymbol{G}$ are different F0 states.

## 8. Choosing the $q$ points

### 8.1 Conversions

With $L$ as above,

$$
\boldsymbol q=2\pi L^{-T}\boldsymbol q_{\rm frac},\qquad
 \boldsymbol q_{\rm frac}=\frac{1}{2\pi}L^{T}\boldsymbol q. \tag{8.1}
$$

A measurement point is a unit direction $\hat{\boldsymbol s}$ and a magnitude $t$, with $\boldsymbol q=t\hat{\boldsymbol s}$. Each one requires the pair $\pm\boldsymbol q$.

### 8.2 Directions

Two rank conditions must both hold. They are different, and the code checks both before any input is written.

- **For $\mathcal D$:** let $S$ have the directions $\hat{\boldsymbol s}_i$ as columns. Each direction gives three numbers, so three non-coplanar directions determine all nine entries with no symmetry input. This requires $\operatorname{rank}S=3$.
- **For $A$:** each direction gives only one number, $\hat{\boldsymbol s}^TA\hat{\boldsymbol s}$. The matrix with entries $\hat{\boldsymbol s}_i^TC_\ell\hat{\boldsymbol s}_i$ must have rank $p_A$. Six directions are needed with no symmetry; fewer suffice when $p_A$ is small.

Symmetry-equivalent directions can pass the first test and fail the second. In $R3c$ BFO, the three directions $(100)$, $(010)$, $(001)$ in $\boldsymbol q_{\rm frac}$ are related by the threefold axis, so they measure the same stiffness. They give rank 1 of 2. The set $(111)$, $(1\bar10)$, $(100)$ gives rank 2 and $\operatorname{rank}S=3$. For a polar crystal a good default is along the axis, in the basal plane, and one oblique direction. The direction along the axis also gives $y=0$ by symmetry, which is a direct test.

Choose from low-index candidates, and take the set with the largest smallest singular value in both conditions. Use at least $\max(3,p_A)$ directions.

### 8.3 Magnitudes

Use three magnitudes per direction, so that one degree of freedom remains after fitting two terms. The stiffness signal grows as $t^2$ and the spiralization signal as $t$, so the stiffness sets the lower bound on $t$. The series truncation sets the upper bound, roughly $t\,r_{\rm max}\lesssim1$ for the important interaction range. For BFO-scale values, a first choice is $t=0.03,\,0.06,\,0.09$ Å$^{-1}$, to be confirmed by convergence tests.

### 8.4 The $k$ mesh and the exchange grid

Use one $\Gamma$-centered mesh for every $q$ of a material, including $q=0$. Insulators do not require $q$ to be commensurate with this mesh. Metals do need the mesh to resolve $q$ near the Fermi surface, so use a convergence series there.

For exchange, take a coarse $\Gamma$-centered grid in $\boldsymbol q_{\rm frac}$, remove $q=0$, and keep one point per set related by $G$ and by $\boldsymbol q\mapsto-\boldsymbol q$.

## 9. Fitting

Every fit below is ordinary linear least squares. The same small routine does all of them.

### 9.1 Slopes and curvatures along each direction

For each direction $\hat{\boldsymbol s}$, fit the three magnitudes separately for each axis:

$$
y_\alpha(t\hat{\boldsymbol s})=v_\alpha t+c_\alpha t^3,\qquad
 g(t\hat{\boldsymbol s})=\kappa\,t^2+b\,t^4. \tag{9.1}
$$

The higher terms are nuisance parameters. The useful results are $\boldsymbol{v}(\hat{\boldsymbol s})$ and $\kappa(\hat{\boldsymbol s})$, which by Eqs. (1.3) and (1.4) are

$$
\boldsymbol{v}(\hat{\boldsymbol s})=2\mathcal D\,\hat{\boldsymbol s},\qquad \kappa(\hat{\boldsymbol s})=\hat{\boldsymbol s}^{T}A\,\hat{\boldsymbol s}. \tag{9.2}
$$

### 9.2 The tensors

Let $V$ have the vectors $\boldsymbol{v}(\hat{\boldsymbol s}_i)$ as columns, in the order of $S$. The free spiralization tensor needs no symmetry input:

$$
\boxed{\mathcal D_{\rm free}=\tfrac12\,V\,S^{+},} \tag{9.3}
$$

where $S^{+}$ is the pseudoinverse, equal to $S^{-1}$ for three directions. Its forbidden part is

$$
\mathcal F=\mathcal D_{\rm free}-\mathcal P_{\mathcal D}[\mathcal D_{\rm free}]. \tag{9.4}
$$

This should vanish within error. An axis, frame or transpose error generally makes it nonzero. An overall sign error does not, so the sign must come from an external anchor.

The reported tensor uses the symmetry basis. Minimize

$$
\sum_{i,\alpha}\Bigl[v_\alpha(\hat{\boldsymbol s}_i)-\sum_\ell d_\ell\,
 2\,\hat{\boldsymbol{e}}_\alpha^{\,T}B_\ell\hat{\boldsymbol s}_i\Bigr]^2. \tag{9.5}
$$

For $A$, the basis is required unless six or more directions are available. Minimize

$$
\sum_i\Bigl[\kappa(\hat{\boldsymbol s}_i)-\sum_\ell a_\ell\,\hat{\boldsymbol s}_i^{T}C_\ell\hat{\boldsymbol s}_i\Bigr]^2. \tag{9.6}
$$

The eigenvalues of $A$ must be positive. A negative eigenvalue means the chosen pattern is not even a local minimum of the exchange energy.

### 9.3 Exchange classes

Stack Eq. (7.11) over the exchange grid and the small-$q$ points:

$$
\min_{\{J_c\}}\sum_m\Bigl[g(\boldsymbol q_m)-\sum_cJ_c\Phi_c(\boldsymbol q_m)\Bigr]^2. \tag{9.7}
$$

Check the rank first. Raise the bond cutoff until the leave-one-out prediction error stops improving. The result gives a second estimate of the stiffness,

$$
A=\frac{1}{2N_{\mathrm m}}\sum_cJ_c\sum_{b\in c}\varepsilon_b\,\boldsymbol{r}_b\boldsymbol{r}_b^{\,T}, \tag{9.8}
$$

which must agree with Eq. (9.6).

### 9.4 Uncertainties

For one linear fit with design matrix $X$, $m$ rows and $p$ parameters,

$$
\hat\sigma^2=\frac{\|\boldsymbol{y}-X\hat{\boldsymbol{x}}\|^2}{m-p},\qquad
 \operatorname{Cov}(\hat{\boldsymbol{x}})=\hat\sigma^2(X^TX)^{-1}. \tag{9.9}
$$

With three magnitudes and two terms each direction has one degree of freedom, so pool $\hat\sigma^2$ over all directions and axes in Eq. (9.1). Carry the resulting slope errors into Eqs. (9.5) and (9.6). Axes from one state share noise, so treat these errors as estimates. Also report the parity residuals of Section 4.5, since a common background cancels in $y$ and would not appear in this fit.

### 9.5 Element-resolved spiralization

Equation (4.8) is a sum over atoms, and Eq. (1.3) is linear in $T$. Applying the same fit to the atom-resolved $T^\mu_\alpha$ gives $\mathcal D=\sum_\mu\mathcal D^\mu$, which can be summed by species. It shows where the SOC energy is collected, within the on-site approximation.

## 10. Predicted properties

### 10.1 The spiral

Minimize Eq. (1.2) over $\boldsymbol q$, then over the unit vector $\hat{\boldsymbol n}$:

$$
\boxed{\begin{gathered}
 \Gamma=\mathcal D A^{-1}\mathcal D^{T},\qquad
 \hat{\boldsymbol n}^*=\text{top eigenvector of }\Gamma\ \text{(eigenvalue $\gamma_{\max}$)},\\
 \boldsymbol q^*=-\tfrac12A^{-1}\mathcal D^{T}\hat{\boldsymbol n}^*,\qquad
 e^*=-\tfrac14\gamma_{\max},\qquad
 \lambda=\frac{2\pi}{|\boldsymbol q^*|}.
 \end{gathered}} \tag{10.1}
$$

Three cases are worth keeping as tests.

- **Scalar case,** $\mathcal D=D\,I$, $A$ scalar: $\lambda=4\pi A/|D|$ and $e^*=-D^2/4A$. Then $\boldsymbol q^*\parallel\hat{\boldsymbol n}^*$, a Bloch helix.
- **Polar case,** $\mathcal D=D[\hat{\boldsymbol{p}}]_\times$: $\hat{\boldsymbol n}^*\perp\hat{\boldsymbol{p}}$, $\boldsymbol q^*=(D/2A_\perp)\,\hat{\boldsymbol{p}}\times\hat{\boldsymbol n}^*$ and $\lambda=4\pi A_\perp/|D|$. This is a cycloid whose spin plane contains $\hat{\boldsymbol{p}}$. Every direction in the basal plane is degenerate at this order, so $\mathcal D$ does not select the propagation direction.
- **Chain,** from Section 6: $q^*=-d/(Ja)$ and $e^*=-d^2/2J$. For $J=10$ meV, $d=1$ meV, $a=3$ Å this gives $\lambda=18.85$ nm, against $18.91$ nm from the exact lattice minimum.

The texture class follows from the form of $\mathcal D$, as in the table of Section 7.4. These are harmonic, homogeneous results. A real spiral ground state also depends on anisotropy and magnetostatics.

### 10.2 Exchange and magnons

For a ferromagnet with moment $M$ in $\mu_{\rm B}$ per site, spin $S=M/2$ and a cone of small angle $\theta$ about spin direction $\hat{\boldsymbol{m}}$, the spiral energy per site is $\theta^2e$ and the spin deviation per site is $S\theta^2/2$. Their ratio is the magnon energy,

$$
\hbar\omega(\boldsymbol k)=\frac{4}{M}\bigl[g(\boldsymbol k)+\hat{\boldsymbol{m}}^{T}\mathcal D\,\boldsymbol k\bigr],
 \qquad D_{\rm sw}=\frac{4A}{M}. \tag{10.2}
$$

Here $\boldsymbol k$ is the propagation direction of the wave $S^x+\mathrm{i} S^y\propto e^{\mathrm{i}(\boldsymbol k\cdot\boldsymbol{r}-\omega t)}$, and $\hat{\boldsymbol{m}}$ follows $\langle\boldsymbol{\sigma}\rangle$, as VASP's magnetization does. The physical moment is opposite, which reverses the sign of the linear term when written in terms of it. A direct spin-dynamics integration on a chain confirmed this sign and prefactor.

The mean-field ordering temperature uses the class constant

$$
k_{\rm B}T_{\rm MF}=\frac23\,C,\qquad
 C=\frac{1}{N_{\mathrm m}}\sum_b\varepsilon_bJ_b=\sum_cJ_c\Phi_c^{\infty},\qquad
 \Phi_c^{\infty}=\frac{1}{N_{\mathrm m}}\sum_{b\in c}\varepsilon_b. \tag{10.3}
$$

This applies when all magnetic sites are equivalent. Mean field overestimates ordering temperatures.

### 10.3 Field and anisotropy

For a cubic helimagnet, a cone of angle $\theta$ gives $\sin^2\!\theta\,e^*-M\mu_{\rm B}B\cos\theta$. The cone closes at the saturation field

$$
B_D=\frac{D^2}{2AM\mu_{\rm B}}. \tag{10.4}
$$

Anisotropy is second order in SOC, so the trace cannot supply it. Take $K$ per magnetic site as the difference between hard and easy directions, from standard SOC total energies at $q=0$. For a chosen pair $(\hat{\boldsymbol s},\hat{\boldsymbol n})$, define $A_s=\hat{\boldsymbol s}^TA\hat{\boldsymbol s}$ and $D_s=\hat{\boldsymbol n}^T\mathcal D\hat{\boldsymbol s}$. The one-dimensional energy per site is

$$
e[\varphi]=A_s(\varphi')^2+D_s\varphi'+K\sin^2\varphi. \tag{10.5}
$$

For a uniaxial easy-axis magnet, a $180^\circ$ wall then costs

$$
\sigma=4\sqrt{A_sK}-\pi|D_s|, \tag{10.6}
$$

which becomes an energy per unit wall area on dividing by $V_{\rm m}$ of Section 10.4. The collinear state gives way to a spiral when $\sigma$ becomes negative:

$$
|D_s|>D_c=\frac{4}{\pi}\sqrt{A_sK}. \tag{10.7}
$$

### 10.4 Units

Let $V_{\rm m}=V_{\rm cell}/N_{\mathrm m}$ be the volume per magnetic site. Dividing a per-site quantity by $V_{\rm m}$ gives the usual micromagnetic parameter:

| Per site | Divide by $V_{\rm m}$ in Å$^3$ | Multiply by |
| --- | --- | --- |
| $A$ in meV Å$^2$ | meV Å$^{-1}$ | $1.602$ for pJ m$^{-1}$ |
| $D$ in meV Å | meV Å$^{-2}$ | $16.02$ for mJ m$^{-2}$ |
| $K$ in meV | meV Å$^{-3}$ | $160.2$ for MJ m$^{-3}$ |

Published normalizations differ, for example per atom or per formula unit, so compare ratios such as $\lambda$ first.

## 11. Checks that make the result usable

Each check addresses a specific way the result can fail.

**C0, T3 and M1: is the operator and trace assembled correctly?**

C0 checks $C_{\downarrow\downarrow}=-C_{\uparrow\uparrow}$, an imaginary antisymmetric $C_{\uparrow\uparrow}$ with zero diagonal, and flip-block Hermiticity. T3 compares $\Lambda_x$ and $\Lambda_y$ from Eq. (4.4) with the $C_{\uparrow\uparrow}$ block of genuine dumps at `SAXIS` along $x$ and $y$. M1 compares `COCC` with the density matrix rebuilt from `CPROJ`, to $10^{-10}$ eV.

**SCF and state: is this the intended spiral?**

Require the final electronic loop to reach `EDIFF`. Require small $M_z$, and $|\delta_a|<1^\circ$ when $n_{\rm twist}=0$. Otherwise record $\delta_a$; they should be linear in $q$. Require $M_a(\boldsymbol q)$ within $5\%$ of $M_a(0)$.

**N0, I0, P0 and E0: does the trace have its exact properties?**

N0 requires $T_\alpha(0)$ below $\max(5\times10^{-5}\ {\rm eV},3\sigma)$ on all three axes. I0 bounds the imaginary residual below $10^{-6}$ eV. P0 compares $T_\alpha(\boldsymbol q)+T_\alpha(-\boldsymbol q)$ with $T_\alpha(\boldsymbol q)-T_\alpha(-\boldsymbol q)$; start at $10\%$ at the smallest $q$ and tighten from data. E0 compares $E(\boldsymbol q)$ with $E(-\boldsymbol q)$.

**Forbidden: do the tensors obey symmetry?**

Require $\mathcal F$ of Eq. (9.4) to vanish within $3\sigma$. Also test directions with a symmetry-required zero, such as $y$ along a polar axis.

**Cross-check: do the two stiffness routes agree?**

Compare Eq. (9.6) with Eq. (9.8).

**Nulls and anchors: is the result physically right?**

If inversion is kept, then $e(-\boldsymbol q,\hat{\boldsymbol n})=e(\boldsymbol q,\hat{\boldsymbol n})$, so $y_\alpha(\boldsymbol q)=0$ at every $q$, not only in the slope. Bcc Fe is the first such test. For sign and magnitude, compare with direct SOC energies on a commensurate supercell of a cheap noncentrosymmetric control. For the method, compare with FLEUR first-order spiral results for BFO [2] and FeGe [3], matching structure, functional and normalization. These are tests of the code, not of experiment: those calculations give about 80 nm against 62 nm for BFO and about 140 nm against about 70 nm for FeGe.

The remaining physical assumptions are compact: one order parameter with one magnetic pattern; SOC at first order on fixed SOC-free states and occupations; all-electron on-site SOC; and one material operator reused across small $q$. SOC-driven twist is second order in the energy and is outside this scheme [4]. The numerical checks of this document confirm the algebra. They do not establish any DFT result.

## 12. One material, from inputs to tensors

1. Read the structure and $\varepsilon_a$. Build $G$ from Eqs. (7.1)–(7.3).
2. Compute $B_\ell$, $C_\ell$ and $n_{\rm twist}$ from Eqs. (7.6)–(7.9).
3. Choose directions and magnitudes, and test both rank conditions of Section 8.
4. Write targets from Eq. (3.1) at $\pm\boldsymbol q$, at $q=0$ and on the exchange grid. Run the SCFs, the `dump_P` captures and the `dump_C` runs.
5. Read $E$ and `M_int`. Compute $\delta_a$ from Eq. (3.3).
6. Form $\Lambda_\alpha$ from Eq. (4.4) and $\boldsymbol{T}$ from Eq. (4.8) for each state.
7. Form $y_\alpha$ and $g$ from Eqs. (1.3) and (1.4).
8. Fit Eq. (9.1), then compute $\mathcal D_{\rm free}$, $\mathcal F$, $\mathcal D$, $A$ and $J_c$.
9. Apply the checks of Section 11.
10. Evaluate Section 10 and convert units. Report the tensors in the POSCAR Cartesian frame, with the stated Hamiltonian and per-site convention.

## References and implementation records

1. M. Heide, G. Bihlmayer and S. Blügel, *Describing Dzyaloshinskii–Moriya spirals from first principles*, Physica B **404**, 2678–2683 (2009). [Author preprint](https://juser.fz-juelich.de/record/5598/files/HBB_FCM08.pdf).
2. B. Xu, S. Meyer, M. J. Verstraete, L. Bellaiche and B. Dupé, *First-principles study of spin spirals in the multiferroic BiFeO$_3$*, Phys. Rev. B **103**, 214423 (2021). [DOI](https://doi.org/10.1103/PhysRevB.103.214423).
3. S. Grytsiuk *et al.*, *Ab initio analysis of magnetic properties of the prototype B20 chiral magnet FeGe*. [arXiv:1909.13545](https://arxiv.org/abs/1909.13545).
4. *Micromagnetic description of twisted spin spirals in the B20 chiral magnet FeGe from first principles*. [arXiv:2103.09800](https://arxiv.org/abs/2103.09800).
5. VASP Wiki, [Spin spirals](https://vasp.at/wiki/Spin_spirals). Generalized Bloch functions and magnetization.
6. VASP Wiki, [Spin-spiral calculations](https://vasp.at/wiki/Spin-spiral_calculations). Symmetry, cutoffs and sphere-moment readback.
7. VASP Wiki, [LSORBIT](https://vasp.at/wiki/LSORBIT). All-electron one-center SOC approximation.
8. [spglib documentation](https://spglib.readthedocs.io/en/v2.8.0/api/autodoc/spglib.spg.html). Symmetry operations in direct fractional coordinates.
9. Project bcc Fe convention tests and user-supplied VASP source excerpts, reviewed 20–25 September 2026, as recorded in Revision 2.4. Executable hashes and full run archives were not supplied with these excerpts.
10. Revision 2.4, *From Heide's Force Theorem to the VASP Trace*, 26 September 2026, for the Patch B run separation, stored `COCC` convention, gate definitions and lab-frame moment contract, which this revision keeps.
