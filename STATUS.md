# Current project status

**Last reconciled:** 2026-09-29 UTC, from the supplied documents and chat evidence.  
**Code checkout inspected:** none in this starter-kit session.  
**Integration branch / base commit:** to record in the actual repository.  
**Current task owner:** unassigned; confirm whether a VS Code session is already working.

## Established

- Mathematics Revision 2.4 is complete. Measured vectors replace redundant
  angular state variables; only F1 offset and F2 tilt remain as input controls.
- bcc Fe results and supplied VASP source support direct lab-frame MAGMOM and
  M_CONSTR, with OSZICAR M_int/MW_int readback for the tested setup.
- The historical N0 null trace passed for its recorded files/builds.
- A self-contained Step 1 implementation spec exists.

These statements do not establish production-build acceptance, new BFO results,
or that the current code already implements the revised convention.

## Work queue

| ID | Work | Status | Owner / branch | Completion evidence |
|---|---|---|---|---|
| REPO-01 | Integrate these files, initialize/reuse Git and connect a private remote | Ready for local integration | Unassigned | Baseline commit, remote identity, clean/understood working tree |
| DMI-01 | Inspect current code and implement or verify Step 1 | Implementation status unverified | Unassigned | Spec acceptance checks and linked session report |
| DMI-02 | Corrected constraint probe and pilot-only runner | Planned after DMI-01 integration | Unassigned | Local runner checks and production smoke-test evidence |
| DMI-03 | Production operator, constraint and F0 pilots | Pending prerequisites | Unassigned | Matched executable/reference and recorded gate results |
| DMI-04 | BFO campaign, paired fit and internal stability checks | Pending pilot results | Unassigned | Accepted dataset, fit and validation report |
| DMI-05 | Independent physical DMI comparisons | Protocol/results outstanding | Unassigned | Matched external-anchor comparisons |

Before claiming DMI-01, inspect the actual branch and any work already done in
VS Code. Do not restart it merely because this starter record says unverified.

## Immediate next action

Complete REPO-01 in the existing pipeline directory without moving source code.
Record the baseline commit and current test results. Then use the Step 1 spec
to assess what is already implemented and finish the remaining work.

## Unresolved production inputs

- Actual repository/environment and reliable local test commands.
- Perlmutter executable path/hash and source/build identity.
- Matching reference and job template.
- Validated sphere radii, F1 LZEROZ policy and F2 initialization.
- Paired trace convergence/noise settings and genuine SOC-axis validation.

These are production follow-ups, not reasons to invent values or skip local
implementation/tests. Second-order SOC remains deferred.

## Handoff records

- [Starter-kit preparation](docs/sessions/2026-09-29-bootstrap.md).
- Add the latest implementation session here when its work is integrated.

Keep this file a current snapshot. Detailed commands and attempts belong in
session logs; durable reasons belong in DECISIONS.
