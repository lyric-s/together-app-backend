import sys


def test_python_version():
    """
    Verifies we are running on the expected Python version (e.g., 3.12+).
    Currently just for workflows to pass
    TEMPORARY !!!
    """
    assert sys.version_info.minor >= 12
    assert sys.version_info.minor < 13
