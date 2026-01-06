import sys


def test_python_version():
    """
    Check that the running Python interpreter is Python 3.12.
    Essentially for testing that the working is working.

    Raises:
        AssertionError: If the interpreter's minor version is less than 12 or is 13 or greater.
    """
    assert sys.version_info.minor >= 12
    assert sys.version_info.minor < 13
