from database.jodi_validator import validate_jodi


def analyze_jodi_relationship(
    jodi_a: str,
    jodi_b: str,
) -> dict:
    """
    Analyze the structural relationship between two Jodi values.

    This function is descriptive only.
    It does not generate predictions.
    """

    jodi_a = validate_jodi(jodi_a)
    jodi_b = validate_jodi(jodi_b)

    digits_a = [int(digit) for digit in jodi_a]
    digits_b = [int(digit) for digit in jodi_b]

    same_jodi = jodi_a == jodi_b

    reversed_jodi = (
        jodi_a[0] == jodi_b[1]
        and jodi_a[1] == jodi_b[0]
    )

    same_first_digit = digits_a[0] == digits_b[0]
    same_second_digit = digits_a[1] == digits_b[1]

    digit_differences = [
        abs(digits_a[index] - digits_b[index])
        for index in range(2)
    ]

    total_digit_difference = sum(
        digit_differences
    )

    same_digit_sum = (
        sum(digits_a) == sum(digits_b)
    )

    return {
        "jodi_a": jodi_a,
        "jodi_b": jodi_b,
        "same_jodi": same_jodi,
        "reversed_jodi": reversed_jodi,
        "same_first_digit": same_first_digit,
        "same_second_digit": same_second_digit,
        "digit_differences": digit_differences,
        "total_digit_difference": (
            total_digit_difference
        ),
        "digit_sum_a": sum(digits_a),
        "digit_sum_b": sum(digits_b),
        "same_digit_sum": same_digit_sum,
    }