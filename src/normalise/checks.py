"""Input checks shared by the normalisation functions."""


def require_str(value: object) -> None:
    """Raise a TypeError unless the value is a str.

    Missing values (None, or NaN from pandas) are not converted to strings here. The caller
    must handle them before calling a normalisation function.

    Args:
        value: The value to check.

    Raises:
        TypeError: If value is not a str.
    """
    if not isinstance(value, str):
        raise TypeError(f"expected str, got {type(value).__name__}")
