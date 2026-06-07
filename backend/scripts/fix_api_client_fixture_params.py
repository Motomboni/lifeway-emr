"""Add missing api_client fixture parameter to test methods that call api_client()."""

import re
from pathlib import Path

TESTS = Path(__file__).resolve().parent.parent / "tests"


def fix_file(path: Path) -> int:
    text = path.read_text(encoding="utf-8")
    if "api_client(" not in text:
        return 0

    changed = 0
    parts = []
    pos = 0
    for m in re.finditer(r"def (test_\w+)\(([^)]*)\):", text):
        if m.group(1) == "test_org":
            continue
        parts.append(text[pos : m.start()])
        params = m.group(2)
        body_start = m.end()
        next_m = re.search(r"\n    def test_|\nclass ", text[body_start:])
        body_end = body_start + next_m.start() if next_m else len(text)
        body = text[body_start:body_end]

        if "api_client(" in body and "api_client" not in params:
            if params.strip():
                params = f"{params}, api_client"
            else:
                params = "api_client"
            changed += 1

        parts.append(f"def {m.group(1)}({params}):")
        pos = body_end

    parts.append(text[pos:])
    if changed:
        path.write_text("".join(parts), encoding="utf-8")
    return changed


def main():
    total = 0
    for path in sorted(TESTS.rglob("*.py")):
        n = fix_file(path)
        if n:
            print(f"{path.relative_to(TESTS.parent)}: {n} methods")
            total += n
    print(f"Fixed {total} methods total")


if __name__ == "__main__":
    main()
