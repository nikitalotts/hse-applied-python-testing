import pytest
from src.links.exceptions import (
    LinkNotFoundError,
    NonUniqueAliasError,
    NonUniqueShortCodeError,
    PermissionDenied,
    UrlAlreadyExists,
    AliasLengthError
)


@pytest.mark.parametrize("exception_class,expected_status,expected_detail", [
    (LinkNotFoundError, 404, "Link not found"),
    (PermissionDenied, 403, "You cannot manage this link."),
])
def test_simple_errors(exception_class, expected_status, expected_detail):
    error = exception_class()

    assert error.status_code == expected_status
    assert error.detail == expected_detail
    assert error.headers is None


@pytest.mark.parametrize("exception_class,arg_name,arg_value,expected_detail", [
    (NonUniqueAliasError, "alias", "myalias", "Alias 'myalias' already exists"),
    (NonUniqueShortCodeError, "code", "abc123", "Short code 'abc123' already exists"),
    (UrlAlreadyExists, "url", "http://test.com", "URL 'http://test.com' already has been shorten"),
    (AliasLengthError, "alias", "bad", "Alias length must be between 4 and 16 symbols"),
])
def test_errors_with_arguments(exception_class, arg_name, arg_value, expected_detail):
    error = exception_class(**{arg_name: arg_value})

    assert error.status_code == 409
    assert error.detail == expected_detail
