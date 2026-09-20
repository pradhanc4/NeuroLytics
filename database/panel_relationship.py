from database.panel_validator import validate_panel


def analyze_panel_relationship(
    panel_a: str,
    panel_b: str,
) -> dict:
    """
    Analyze the structural relationship between two Panel values.

    This function is descriptive only.
    It does not generate predictions.
    """

    panel_a = validate_panel(panel_a)
    panel_b = validate_panel(panel_b)

    digits_a = [int(digit) for digit in panel_a]
    digits_b = [int(digit) for digit in panel_b]

    same_panel = panel_a == panel_b

    reversed_panel = (
        panel_a[0] == panel_b[2]
        and panel_a[1] == panel_b[1]
        and panel_a[2] == panel_b[0]
    )

    same_first_digit = (
        digits_a[0] == digits_b[0]
    )

    same_second_digit = (
        digits_a[1] == digits_b[1]
    )

    same_third_digit = (
        digits_a[2] == digits_b[2]
    )

    digit_differences = [
        abs(
            digits_a[index]
            - digits_b[index]
        )
        for index in range(3)
    ]

    total_digit_difference = sum(
        digit_differences
    )

    same_digit_sum = (
        sum(digits_a)
        == sum(digits_b)
    )

    return {
        "panel_a": panel_a,
        "panel_b": panel_b,
        "same_panel": same_panel,
        "reversed_panel": reversed_panel,
        "same_first_digit": same_first_digit,
        "same_second_digit": same_second_digit,
        "same_third_digit": same_third_digit,
        "digit_differences": digit_differences,
        "total_digit_difference": (
            total_digit_difference
        ),
        "digit_sum_a": sum(digits_a),
        "digit_sum_b": sum(digits_b),
        "same_digit_sum": same_digit_sum,
    }