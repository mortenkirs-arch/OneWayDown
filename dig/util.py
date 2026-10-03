"""Small helpers shared across modules."""


def fmt(n):
    """Format a number compactly: 1234 -> 1.23K."""
    n = float(n)
    for value, suffix in ((1e15, "Q"), (1e12, "T"), (1e9, "B"), (1e6, "M"), (1e3, "K")):
        if abs(n) >= value:
            return f"{n / value:.2f}{suffix}"
    return f"{n:.1f}" if n != int(n) and abs(n) < 10 else f"{int(n)}"


def shade(color, f):
    return tuple(max(0, min(255, int(c * f))) for c in color)
