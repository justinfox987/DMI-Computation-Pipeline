# Math-document review: what needs to change

Reviewed the supplied 11-page `heide_math.pdf`, titled *From Heide's Force
Theorem to the VASP Trace: A Piece-by-Piece Derivation*, dated July 2026.
Page numbers below are the printed/PDF page numbers. This is a revision guide,
not a replacement PDF or a claim that the pending physics validation has passed.

## Verdict

The recent parent-rule, executable and probe changes do **not** replace the
force-theorem/PAW foundation or the bilinear DMI Hamiltonian. They change how
we obtain and certify the states used in that calculation.

However, this particular PDF predates the explicit two-trace observable,
Patch B inputs and the full decorated-family fitting formulation. It needs
substantive updates to its observable/model sections and implementation bridge,
plus a short constrained-state subsection. Calling all the changes operational
would leave mathematical equations that no longer describe production.

## 1. Preserve the central contraction

The core remains a first-order, frozen-SOC-free-state trace:

\[
T(c;\hat n)=\sum_{\mu nk s}w_k f^{(0)}_{nk}(c)
\,[c^\mu_{nks}(c)]^\dagger
 C^\mu_{ss}(\hat n)\,c^\mu_{nks}(c).
\]

Here the configuration descriptor `c` and the projector coefficient vector
are distinct objects despite the shared letter; the revised manuscript should
give them distinct notation. Each configuration uses its own projections and
occupations. The PAW on-site reduction, spin-diagonal contraction for generic
spirals, and density-matrix/per-state equivalence remain the framework.

This does not establish the numerical validity of first-order SOC or a fixed
bilinear model for every constrained state. The planned scans and T9 anchors
still test those approximations.

## 2. Replace the production single-trace equation

**Locations:** abstract; section 1.3, Pin 2 (p.3); section 8.1, Eq. (23)
(p.9); section 9 anchor formula (p.10); Appendix B (p.11).

Define generalized parity on the full configuration:

\[
c_+=(q,\psi,\{\theta_a\},W),\qquad
c_-=(-q,-\psi,\{\theta_a\},W),
\]

where the winding assignment W and reference sublattice signs stay fixed.
Use the same measurement axis on both sides. Production is

\[
\boxed{y_m=\frac{T(c_+;\hat n)-T(c_-;\hat n)}{N_m}.}
\]

The ideal symmetry relation `T(c_-)=-T(c_+)` gives the old `2*T(c_+)/N_m`
as a limiting identity. Retain that as a theorem/check under its hypotheses,
not permission to omit the negative configuration. There is no new factor
of one-half. P0 still checks the sum under Rev 2; subtraction is not a license
to accept the old large contaminated common mode.

Add the uncertainty equations, with V the covariance of the two raw traces:

\[
\operatorname{Var}(y)=\frac{\sigma_+^2+\sigma_-^2-2V}{N_m^2},\qquad
\operatorname{Var}(T_++T_-)=\sigma_+^2+\sigma_-^2+2V.
\]

The sum and difference therefore do not share one interchangeable noise
threshold. Shared projections across axes and shared controls across fits
can also create covariance; account for it in reported comparisons.

## 3. Extend the flat-spiral model to realized decorated pairs

**Locations:** section 2.1, Eq. (1) (p.3); section 8.3, Eqs. (24)–(25)
(p.9); Appendix C item 4 (p.11).

The present ansatz is the F0 special case. Include sublattice decorations and
cones, with the fixed reference signs explicit:

\[
\hat S_{Ra}=\epsilon_a\{
 \sin\theta_a[\cos\phi_{Ra}\,\hat u+\sin\phi_{Ra}\,\hat v]
 +\cos\theta_a\,\hat n\},\quad
\phi_{Ra}=2\pi q_{\rm frac}\!\cdot(R+\tau_a)_{\rm frac}+\psi_a.
\]

This describes the physical model frame. Production VASP states use internal
axis z; the measurement axis is implemented by rotating the operator. For F2,
the frozen sublattice has sin(theta)=0, so its azimuth is irrelevant. Physical
cone angles must be interpreted with the epsilon signs, not by ignoring the
sign of the frozen moment.

Define an unnormalized single-configuration kernel over canonical bonds once:

\[
A_j(c;\hat n)=\sum_{b\in\mathcal B_{\rm can}}
\epsilon_{a_b}\epsilon_{a'_b}\sin\theta_{a_b}(c)\sin\theta_{a'_b}(c)
\sin\!\left[2\pi q_{\rm frac}\!\cdot r_{b,\rm frac}
             +\psi_{a'_b}(c)-\psi_{a_b}(c)\right]
\hat n\!\cdot\mathbf p_{bj}.
\]

Here p_bj is the symmetry-propagated basis vector for parameter j, including
bond-reversal and axial-vector signs. Explain the lattice averaging that leaves
the axis component of the cone cross product; do not claim the whole local
cross product is always parallel to the axis for conical spins.

The measured row is

\[
\boxed{M_{mj}=\frac{A_j(c_+^{\rm realized};\hat n)
                         -A_j(c_-^{\rm realized};\hat n)}{N_m},
\qquad y=Mx.}
\]

Each side supplies its own valid realized angles. Exact partners recover the
old `2*A(c_+)/N_m` row. This is the established decorated-pair formulation,
not a proposed new kernel. It does not correct arbitrary changes of electronic
state or moment magnitude outside the assumed unit-spin model.

Describe symmetry-reduced orbit parameters and a stacked solve, rather than
implying that three separate flat-spiral component fits identify every bond.
F0 alone is rank-deficient for the current nine-parameter material model.

## 4. Make rotation order explicit

**Locations:** sections 2.3/4.2/8.2 and Appendix A.

Keep the spin rotation, but state the order:

\[
C(\hat n)=U^\dagger(\hat n)C_zU(\hat n),\qquad
\Pi_z(X)=\tfrac12[X+(\sigma_z\otimes I)X(\sigma_z\otimes I)].
\]

Contract `Pi_z(C(n))` with the frozen internal-z state. Rotate the **full**
operator before selecting its diagonal spin blocks. In general,

\[
\Pi_z(U^\dagger C_zU)\ne U^\dagger\Pi_z(C_z)U.
\]

The original flip blocks contribute to rotated diagonal blocks. They are not
zero; full Hermiticity requires `C_ud=C_du^dagger`, not Hermiticity of each
flip block separately. T3 pins the VASP sign/order convention and validates
the genuine dumps. Distinguish this measurement axis from frame adapters.

## 5. Add the constrained-state mathematics

**New subsection or appendix;** link to the probe protocol for numerical details.

For mode 1, use the weighted sphere moment MW, not an interchangeable
projected or unweighted moment:

\[
E_p=\lambda\sum_I|P_{\perp,I}MW_I|^2,\quad
P_{\perp,I}=I-\hat m_I\hat m_I^T,\quad
B_I^c=2\lambda P_{\perp,I}MW_I.
\]

The [VASP constraint definition](https://vasp.at/wiki/I_CONSTRAINED_M) uses
the smoothed moment printed as MW_int. For fixed magnitude,

\[
E_{p,I}=\lambda|MW_I|^2\sin^2\beta_I,\qquad
\frac{\partial E_{p,I}}{\partial\beta_I}
=\lambda|MW_I|^2\sin(2\beta_I).
\]

Parallel and antiparallel directions have zero penalty. At 90° the angular
derivative vanishes while the penalty is nonzero. This explains the signed
realization gate, psi continuation and near-target F2 starts. It does not
prove that the full SCF must remain at that point.

At stationary finite lambda, the state is a solution of an augmented constrained
problem. The production trace inserts SOC, not the penalty energy. Do not
add/subtract E_p from the first-order SOC contraction. T5/T6/T7 test the
transferability of the resulting model across constraint strength and states.
Small E_p alone proves neither the target sign nor an unbiased DMI estimate.

## 6. Replace the Patch A implementation bridge

**Locations:** sections 1.1/1.2/1.3, 6, 7.1/7.4/7.5, Appendix B.

- CPROJ, COCC and FERWE come from the same SOC-free PRE_LOOP capture, before
  orbital updates. COCC is rebuilt from those input projections and weights.
- FERWE.dat is the primary occupation/weight source. Stage-2 EIGENVAL is a
  cross-check. The PDF's explicit prohibition on FERWE is obsolete.
- Rank files have explicit global indices; remove empirical block/cyclic
  ordering and the retired reader names. Enforce completeness/uniqueness.
- The material operator is separate from the per-configuration projections.
  Its lack of explicit occupation weights does not make it independent of
  the potential. Reusing one reference operator across configurations is a
  transferability assumption to state and justify, not an exact consequence
  of spin rotation. Axis rotation at fixed radial operator is a separate issue.

These are mathematical-input/provenance corrections; the c-dagger-C-c
contraction itself is unchanged.

## 7. Correct or qualify existing derivation details

### Bond counting: Eq. (24), p.9

With H summed once over undirected bonds, exact flat parity gives

\[
E_{\rm DM}=\frac{2}{N_m}\sum_{b\in\mathcal B_{\rm can}}h_b(q)
=\frac{1}{N_m}\sum_{b\in\mathcal B_{\rm directed}}h_b(q),
\quad h_b=\epsilon_i\epsilon_j(\hat n\cdot d_b)\sin(q\cdot r_b).
\]

Eq. (24)'s `2/N_m` is correct only if its neighbor enumeration counts each
bond once. With the usual full neighbor list it is too large by two; Eq. (25)
explicitly uses canonical bonds. Define the enumeration consistently. This is
a manuscript ambiguity/error to resolve, not an instruction to change the
current canonical-bond kernel's normalization.

### PAW reduction: section 3.2 and Appendix C item 1

For a local operator, write the usual PAW decomposition as the smooth
expectation plus an AE-minus-PS one-center correction. Under one-center
completeness, the smooth contribution inside each sphere cancels its PS
subtraction; neglect the remaining outside-sphere SOC to obtain the AE
one-center approximation. Smooth/nodeless pseudo waves alone do not imply
zero SOC matrix elements. The PDF's description of both terms as vanishing
"subtraction pieces" should be corrected.
The final AE one-center formula agrees with the
[documented VASP SOC approximation](https://vasp.at/wiki/LSORBIT).

In Eq. (12), put the l_i=l_j selection rule on the angular matrix element;
the displayed radial integral alone need not vanish for different l.

### Selection-rule domain and nulls: sections 5, 8.3 and 9

Keep the generic-q condition `q not in G`. The lattice-sum argument does not
remove flip contributions at q=0. Explain N0 separately: it checks the
z-projected operator on an in-plane collinear SOC-free state using the spin-only
C2x symmetry. It is not an application of the generic-q selection rule.

A TRIM q does not by itself make an arbitrary decorated configuration its own
generalized-parity partner: the decorations and reciprocal-vector/basis gauge
also have to match. Do not derive the production noise floor from presumed
TRIM nulls; use the measured paired replicas.

### Imaginary-part gate: section 7.6

Hermiticity implies real expectations in exact arithmetic. In practice bound
absolute imaginary residuals above floating-point/output precision. A real
result is necessary, not sufficient: a transposed Hermitian matrix remains
Hermitian and can yield a wrong but entirely real answer. I0 cannot certify
every sign, transpose or indexing convention.

## 8. Update validation and approximation claims

Revise section 9 and Appendix C to include C0/W0/M1, N0, P0, I0, T3, signed
R0, paired noise, lambda/decoration/cross-family checks and T9. M0 is restricted
to same-state build/debug validation. Remove unsupported current-build PASS
claims and the old use of TRIMs to establish production noise.

Separate assumptions about atom-centered SOC, first-order/frozen-state response,
fixed occupations, PAW completeness, common radial operator, and the unit-spin
bilinear model's transferability across constrained configurations. Initializing
a state differently or hashing a binary introduces no new Hamiltonian term.
Those changes establish that the states actually satisfy the premises.

## Recommended manuscript work

Retain the trace derivation as the foundation, repair section 3.2 and the domain
qualifications, rewrite sections 7–9 and Appendix B for Patch B and paired
decorated fitting, and add the constrained-state subsection. This is a focused
revision of the companion, not a replacement physical theory. The separate
decorated-spiral derivation, if maintained elsewhere, should use the same pair
normalization, sign conventions and realized-state kernel.
