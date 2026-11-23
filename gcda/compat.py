"""Small compatibility shims for third-party API changes."""


def bicop_sample(bicop, n: int, seeds: list[int] | None = None):
    """Draw from a pv.Bicop: `sample` in pyvinecopulib >= 1.0, `simulate` before.

    Both produce identical draws for the same seeds (checked in the audit with
    pyvinecopulib 1.0.1); this avoids the deprecation warning on new versions
    while keeping 0.7.x working.
    """
    seeds = seeds or []
    method = getattr(bicop, "sample", None) or bicop.simulate
    return method(n, seeds=seeds)
