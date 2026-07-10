"""Post-install .env fixups for the launchers (run.bat / run.sh).

- KRONOS_PATH: if unset or pointing at a directory that doesn't exist,
  repoint it at the repo-local ./Kronos clone (downloaded by run.bat).
- JWT_SECRET: generate one if blank — needed for auth tokens and to
  encrypt Binance credentials saved from the Settings page.

Idempotent: never touches a value that already works.
"""

import re
import secrets
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = ROOT / ".env"


def get_value(text: str, key: str) -> str | None:
    m = re.search(rf"^{key}=(.*)$", text, re.M)
    return m.group(1).strip().strip('"') if m else None


def set_value(text: str, key: str, line: str) -> str:
    # Replacement via lambda so Windows backslashes in `line` aren't
    # interpreted as regex escapes.
    if re.search(rf"^{key}=", text, re.M):
        return re.sub(rf"^{key}=.*$", lambda _: line, text, count=1, flags=re.M)
    return text.rstrip("\n") + f"\n{line}\n"


def main() -> None:
    text = ENV_PATH.read_text(encoding="utf-8")
    changed = []

    kronos_path = get_value(text, "KRONOS_PATH")
    local_kronos = ROOT / "Kronos"
    if (not kronos_path or not Path(kronos_path).is_dir()) and (local_kronos / "model").is_dir():
        text = set_value(text, "KRONOS_PATH", f'KRONOS_PATH="{local_kronos}"')
        changed.append(f"KRONOS_PATH -> {local_kronos}")

    if not get_value(text, "JWT_SECRET"):
        text = set_value(text, "JWT_SECRET", f"JWT_SECRET={secrets.token_urlsafe(48)}")
        changed.append("JWT_SECRET generated")

    if changed:
        ENV_PATH.write_text(text, encoding="utf-8")
        for c in changed:
            print(f"[env] {c}")
    else:
        print("[env] no changes needed")


if __name__ == "__main__":
    main()
