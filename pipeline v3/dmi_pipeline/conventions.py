"""Conventions shared by the dump readers and gates; no process-local gate pins.

CSO's off-diagonal packing must still be measured by T3 before rotation.
"""

UNDETERMINED = object()
VASP_BUILD_ID = UNDETERMINED
DUMP_FORMAT_VERSION = 1
UU_IDX, DD_IDX = 0, 3
# COCC_FROM_INPUT: IS = ISP + bra_spin + 2*ket_spin (Fortran ISP=1).
# This is a density-matrix storage convention, not a CSO rotation pin.
COCC_SPIN_BLOCKS = ((0, 0), (1, 0), (0, 1), (1, 1))
N0_FLOOR_EV = 5e-5
