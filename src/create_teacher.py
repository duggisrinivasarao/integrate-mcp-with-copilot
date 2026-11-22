import getpass
import json
from pathlib import Path
import secrets

from src.teacher_auth import PASSWORD_SALT_BYTES, password_hash


TEACHERS_FILE = Path(__file__).with_name("teachers.json")


def main() -> None:
    username = input("Teacher username: ").strip()
    if not username or len(username) > 128:
        raise SystemExit("Username must contain 1 to 128 characters")

    password = getpass.getpass("Teacher password (at least 12 characters): ")
    if len(password) < 12:
        raise SystemExit("Password must contain at least 12 characters")
    if password != getpass.getpass("Confirm password: "):
        raise SystemExit("Passwords do not match")

    if TEACHERS_FILE.exists():
        try:
            data = json.loads(TEACHERS_FILE.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise SystemExit(f"Could not read {TEACHERS_FILE}: {error}") from error
        if not isinstance(data, dict) or not isinstance(data.get("teachers"), dict):
            raise SystemExit(f"{TEACHERS_FILE} has an invalid format")
    else:
        data = {"teachers": {}}

    salt = secrets.token_bytes(PASSWORD_SALT_BYTES)
    data["teachers"][username] = {
        "salt": salt.hex(),
        "password_hash": password_hash(password, salt).hex(),
    }

    try:
        TEACHERS_FILE.write_text(
            json.dumps(data, indent=2) + "\n",
            encoding="utf-8",
        )
        TEACHERS_FILE.chmod(0o600)
    except OSError as error:
        raise SystemExit(f"Could not write {TEACHERS_FILE}: {error}") from error
    print(f"Teacher account saved to {TEACHERS_FILE}")


if __name__ == "__main__":
    main()
