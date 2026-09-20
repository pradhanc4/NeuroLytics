from collections import Counter


def analyze_panna_structure(panna: str) -> dict:
    """
    Analyze the structural characteristics of a Panna.

    This function does not make predictions.
    It only describes the digit structure of a Panna.
    """

    if panna is None:
        raise ValueError("Panna is required.")

    panna = str(panna).strip()

    if not panna:
        raise ValueError("Panna is required.")

    if not panna.isdigit():
        raise ValueError(
            "Panna must contain digits only."
        )

    if len(panna) != 3:
        raise ValueError(
            "Panna must contain exactly 3 digits."
        )

    digits = [int(digit) for digit in panna]

    digit_counts = Counter(digits)

    unique_digits = sorted(
        digit_counts.keys()
    )

    repeated_digit_count = sum(
        count - 1
        for count in digit_counts.values()
        if count > 1
    )

    return {
        "panna": panna,
        "digits": digits,
        "sorted_digits": sorted(digits),
        "unique_digits": unique_digits,
        "unique_digit_count": len(unique_digits),
        "repeated_digit_count": repeated_digit_count,
        "has_repeated_digit": repeated_digit_count > 0,
    }