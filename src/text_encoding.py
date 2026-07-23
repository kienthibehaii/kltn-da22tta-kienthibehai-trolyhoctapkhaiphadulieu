import unicodedata
from typing import Any


def _build_vietnamese_mojibake_map() -> dict[str, str]:
    mapping: dict[str, str] = {}
    for start, end in ((0x00C0, 0x017F), (0x1EA0, 0x1EF9)):
        for codepoint in range(start, end + 1):
            char = chr(codepoint)
            if "LATIN" not in unicodedata.name(char, ""):
                continue
            raw = char.encode("utf-8")
            for encoding in ("cp1252", "latin1"):
                try:
                    broken = raw.decode(encoding)
                except UnicodeDecodeError:
                    continue
                if broken != char:
                    mapping[broken] = char
    return dict(sorted(mapping.items(), key=lambda item: len(item[0]), reverse=True))


_MOJIBAKE_MAP = _build_vietnamese_mojibake_map()
_EXTRA_MAP = {
    "\u00c6\u00b0": "\u01b0",
    "\u00c6\u00af": "\u01af",
    "\u00c6\u00a1": "\u01a1",
    "\u00c6\u00a0": "\u01a0",
}


def repair_mojibake_text(value: str) -> str:
    fixed = value
    for _ in range(4):
        previous = fixed
        for broken, correct in _MOJIBAKE_MAP.items():
            fixed = fixed.replace(broken, correct)
        for broken, correct in _EXTRA_MAP.items():
            fixed = fixed.replace(broken, correct)
        if fixed == previous:
            break
    return fixed


def repair_mojibake_obj(value: Any) -> Any:
    if isinstance(value, str):
        return repair_mojibake_text(value)
    if isinstance(value, list):
        return [repair_mojibake_obj(item) for item in value]
    if isinstance(value, dict):
        return {key: repair_mojibake_obj(item) for key, item in value.items()}
    return value
