def percentage(value: object, fallback: str = "—") -> str:
    if value is None:
        return fallback
    return f"{float(value):.0f}%"


def label(value: object) -> str:
    return str(value).replace("_", " ").title()
