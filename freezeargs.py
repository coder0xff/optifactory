"""Utility to make functions taking dictionaries into immutable arguments compatible with cache."""

import functools

from frozendict import frozendict


def freezeargs(func):
    """Convert a mutable dictionary into immutable.
    Useful to be compatible with cache
    """

    @functools.wraps(func)
    def wrapped(*args, **kwargs):
        args = (frozendict(arg) if isinstance(arg, dict) else arg for arg in args)
        kwargs = {k: frozendict(v) if isinstance(v, dict) else v for k, v in kwargs.items()}
        return func(*args, **kwargs)
    return wrapped
