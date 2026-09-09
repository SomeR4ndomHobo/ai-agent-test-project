import re
def normalize_text(text: str):

    text = text.upper()

    text = text.replace(
        "|",
        "I"
    )

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text.strip()