"""Trivial harness sanity + engine import smoke tests.

These prove the test/lint/format harness is alive and that the locked
environment can import the ``stockroom`` package and read its version.
"""


def test_harness_runs() -> None:
    """The pytest harness executes and a trivial assertion holds."""
    assert 1 + 1 == 2


def test_import_stockroom_exposes_version() -> None:
    """``import stockroom`` succeeds and exposes a string ``__version__``."""
    import stockroom

    assert isinstance(stockroom.__version__, str)
    assert stockroom.__version__
