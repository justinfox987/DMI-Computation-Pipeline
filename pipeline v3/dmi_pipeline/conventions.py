"""Conventions shared by the dump readers and checks.

CSO.dat and COCC.dat store blocks in the order uu, ud, du, dd with the ket index
first (math Section 4.2). C0's handedness condition pins the flip-block order
from the z dump alone.
"""

UU_IDX, DD_IDX = 0, 3
N0_FLOOR_EV = 5e-5
