"""Utility to make functions taking dictionaries into immutable arguments compatible with cache."""

import functools

from frozendict import frozendict


def freezeargs(func):
    """Decorator to convert mutable dict arguments to immutable frozendicts.

    Precondition:
        func is a callable

    Postcondition:
        returns a wrapped version of func
        wrapped version converts dict args/kwargs to frozendicts before calling func
        useful for making functions compatible with @cache decorator

    Args:
        func: function to wrap

    Returns:
        wrapped function that freezes dict arguments
    """

    @functools.wraps(func)
    def wrapped(*args, **kwargs):
        """Convert dict arguments to frozendicts and call the wrapped function.

        Precondition:
            args and kwargs can contain any types including dicts

        Postcondition:
            all dict arguments converted to frozendicts
            original function called with frozen arguments
            returns result from original function
        """
        args = (frozendict(arg) if isinstance(arg, dict) else arg for arg in args)
        kwargs = {k: frozendict(v) if isinstance(v, dict) else v for k, v in kwargs.items()}
        return func(*args, **kwargs)
    return wrapped
