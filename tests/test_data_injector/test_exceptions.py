# tests/test_data_injector/test_exceptions.py
from pyre.data_injector.exceptions import InjectionError


def test_injection_error_is_exception():
    err = InjectionError("field 'x' is missing")
    assert isinstance(err, Exception)
    assert "field 'x' is missing" in str(err)


def test_injection_error_can_chain():
    cause = ValueError("bad value")
    try:
        raise InjectionError("coercion failed") from cause
    except InjectionError as err:
        assert err.__cause__ is cause
