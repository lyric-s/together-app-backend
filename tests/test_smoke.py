import sys


def test_python_version():
    """
    Verify the running Python interpreter is Python 3.12.

    Raises:
        AssertionError: If the major version is not 3, or if the minor version is less than 12 or is 13 or greater.
    """
    assert sys.version_info.major == 3
    assert sys.version_info.minor >= 12
    assert sys.version_info.minor < 13
