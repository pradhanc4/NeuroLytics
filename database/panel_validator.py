class PanelValidationError(ValueError):
    """Raised when a Panel value is invalid."""


def validate_panel(value: str) -> str:
    """
    Validate and normalize a Panel value.

    A valid Panel must contain exactly three numeric digits.
    Leading zeros are preserved.
    """

    if value is None:
        raise PanelValidationError(
            "Panel is required."
        )

    value = str(value).strip()

    if not value:
        raise PanelValidationError(
            "Panel is required."
        )

    if not value.isdigit():
        raise PanelValidationError(
            "Panel must contain digits only."
        )

    if len(value) != 3:
        raise PanelValidationError(
            "Panel must contain exactly 3 digits."
        )

    return value