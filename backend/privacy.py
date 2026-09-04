import re


_MOBILE_PHONE_PATTERN = re.compile(
    r"(?<!\d)010(?:-\d{4}-| \d{4} |\d{4})\d{4}(?!\d)"
)
_STUDENT_ID_PATTERN = re.compile(r"(?<!\d)\d{10}(?!\d)")
_NAME_PATTERN = re.compile(
    r"(?P<prefix>(?:제\s+)?이름(?:은|이)\s*|이름\s*:\s*)"
    r"(?P<name>[가-힣]{2,5}?)"
    r"(?=입니다|이고|이며|이에요|예요|라고|[\s,.!?]|$)"
)


def mask_personal_data(text: str) -> str:
    masked = _MOBILE_PHONE_PATTERN.sub("***-****-****", text)
    masked = _STUDENT_ID_PATTERN.sub("**********", masked)
    return _NAME_PATTERN.sub(r"\g<prefix>***", masked)
