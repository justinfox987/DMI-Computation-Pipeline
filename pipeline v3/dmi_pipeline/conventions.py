"""Only the conventions needed through N0; no process-local gate pins.

Frame evidence and tolerances: implementation Rev 2 sections 2.2 and 5.4.
CSO's off-diagonal packing must still be measured by T3 before rotation.
"""

UNDETERMINED = object()
VASP_BUILD_ID = UNDETERMINED
DUMP_FORMAT_VERSION = 1
UU_IDX, DD_IDX = 0, 3
# COCC_FROM_INPUT: IS = ISP + bra_spin + 2*ket_spin (Fortran ISP=1).
# This is a density-matrix storage convention, not a CSO rotation pin.
COCC_SPIN_BLOCKS = ((0, 0), (1, 0), (0, 1), (1, 1))
FRAME_MAGMOM = "lab"
FRAME_MCONSTR = FRAME_MINT = "unwound"
FRAME_CONE = "internal_z_cone"
CSO_ROTATION_VALIDATED = False
F1_USES_LZEROZ = UNDETERMINED
TOL_PHI_DEG = TOL_THETA_DEG = 1.0
TOL_MOMENT_REL = 0.05
N0_FLOOR_EV = 5e-5
