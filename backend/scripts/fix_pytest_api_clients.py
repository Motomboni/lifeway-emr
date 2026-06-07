"""
One-off helper: add api_client fixture param and replace APIClient boilerplate.
Run from backend/: python scripts/fix_pytest_api_clients.py
"""

import re
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent.parent / "tests"

# (old two-line pattern, replacement single line) — token/user name from group
REPLACEMENTS = [
    (
        re.compile(
            r"(\n        )client = APIClient\(\)\n        client\.credentials\("
            r'HTTP_AUTHORIZATION=f[\'"]Bearer \{(\w+)\}[\'"]\)',
            re.MULTILINE,
        ),
        r"\1client = api_client(token=\2)",
    ),
    (
        re.compile(
            r"(\n        )client = APIClient\(\)\n        client\.force_authenticate\(user=(\w+)\)",
            re.MULTILINE,
        ),
        r"\1client = api_client(user=\2)",
    ),
    (
        re.compile(
            r"(\n        )client = APIClient\(\)\n        client\.credentials\("
            r'HTTP_AUTHORIZATION=f"Bearer \{(\w+)\}"\)\n        client\.credentials\(',
            re.MULTILINE,
        ),
        r"\1client = api_client(token=\2)",
    ),
]


def ensure_api_client_param(sig_params: str) -> str:
    if "api_client" in sig_params:
        return sig_params
    if sig_params.strip() == "self":
        return "self, api_client"
    return f"{sig_params}, api_client"


def patch_file(path: Path) -> bool:
    text = path.read_text(encoding="utf-8")
    if "APIClient()" not in text:
        return False

    original = text
    for pattern, repl in REPLACEMENTS:
        text = pattern.sub(repl, text)

    if text == original:
        return False

    # Add api_client to def test_* / def test_* methods that now use api_client(
    def add_fixture(match):
        params = match.group(1)
        if "api_client" in params:
            return match.group(0)
        return f"def {match.group(2)}({ensure_api_client_param(params)})"

    text = re.sub(
        r"def (test_\w+)\((self(?:, [^)]*)?)\)",
        lambda m: f"def {m.group(1)}({ensure_api_client_param(m.group(2))})",
        text,
    )
    # Methods that gained api_client(...) but are missing the fixture param
    for m in re.finditer(r"def (test_\w+)\(([^)]*)\):", text):
        if m.group(1) == "test_org":
            continue
        params = m.group(2)
        body_start = m.end()
        next_m = re.search(r"\n    def test_|\nclass ", text[body_start:])
        body_end = body_start + next_m.start() if next_m else len(text)
        body = text[body_start:body_end]
        if "api_client(" in body and "api_client" not in params:
            new_params = ensure_api_client_param(params)
            text = text[: m.start()] + f"def {m.group(1)}({new_params}):" + text[m.end() :]

    path.write_text(text, encoding="utf-8")
    return True


def main():
    changed = []
    for path in sorted(TESTS_DIR.rglob("test_*.py")):
        if patch_file(path):
            changed.append(path.relative_to(TESTS_DIR.parent))
    print(f"Patched {len(changed)} files:")
    for p in changed:
        print(f"  - {p}")


if __name__ == "__main__":
    main()
