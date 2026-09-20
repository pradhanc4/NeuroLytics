class JodiValidationError(ValueError):
    """Raised when a Jodi value is invalid."""


def validate_jodi(value: str) -> str:
    """
    Validate and normalize a Jodi value.

    A valid Jodi must contain exactly two numeric digits.
    Leading zeros are preserved.
    """

    if value is None:
        raise JodiValidationError(
            "Jodi is required."
        )

    value = str(value).strip()

    if not value:
        raise JodiValidationError(
            "Jodi is required."
        )

    if not value.isdigit():
        raise JodiValidationError(
            "Jodi must contain digits only."
        )

    if len(value) != 2:
        raise JodiValidationError(
            "Jodi must contain exactly 2 digits."
        )

    return value