"""Shared candidate copula family set for pairwise and conditional fitting."""

import pyvinecopulib as pv

DEFAULT_BICOP_FAMILIES = [
    pv.BicopFamily.indep,
    pv.BicopFamily.gaussian,
    pv.BicopFamily.student,
    pv.BicopFamily.clayton,
    pv.BicopFamily.gumbel,
    pv.BicopFamily.frank,
    pv.BicopFamily.joe,
]
