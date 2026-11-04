"""Helpers shared by the tests."""


def bn(*code_points: int) -> str:
    """Build a string from Unicode code points.

    Tests build Bangla text this way so that every character is visible as a number and so that
    no editor or tool can silently change the characters being tested.
    """
    return "".join(chr(code_point) for code_point in code_points)
