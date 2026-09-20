class PannaValidationError(ValueError):
    """Raised when a Panna value is invalid."""


def validate_panna(value: str) -> str:
    """
    Validate and normalize a Panna value.

    A valid Panna must contain exactly three numeric digits.
    Leading zeros are preserved.
    """

    if value is None:
        raise PannaValidationError(
            "Panna is required."
        )

    value = str(value).strip()

    if not value:
        raise PannaValidationError(
            "Panna is required."
        )

    if not value.isdigit():
        raise PannaValidationError(
            "Panna must contain digits only."
        )

    if len(value) != 3:
        raise PannaValidationError(
            "Panna must contain exactly 3 digits."
        )

    return value