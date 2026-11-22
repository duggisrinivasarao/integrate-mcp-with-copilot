import hashlib
import json
from pathlib import Path
import secrets


PASSWORD_ITERATIONS = 600_000
PASSWORD_SALT_BYTES = 16
PASSWORD_HASH_BYTES = 32


def password_hash(password: str, salt: bytes) -> bytes:
    return hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        PASSWORD_ITERATIONS,
        dklen=PASSWORD_HASH_BYTES,
    )


def verify_password(password: str, salt_hex: str, password_hash_hex: str) -> bool:
    try:
        salt = bytes.fromhex(salt_hex)
        expected_hash = bytes.fromhex(password_hash_hex)
    except ValueError:
        return False

    if len(salt) != PASSWORD_SALT_BYTES or len(expected_hash) != PASSWORD_HASH_BYTES:
        return False
    actual_hash = password_hash(password, salt)
    return secrets.compare_digest(actual_hash, expected_hash)


def load_teacher_accounts(path: Path) -> dict[str, dict[str, str]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("teachers"), dict):
        raise ValueError("Expected a JSON object with a teachers object")

    teachers = data["teachers"]
    for username, account in teachers.items():
        if (
            not isinstance(username, str)
            or not username
            or not isinstance(account, dict)
            or not isinstance(account.get("salt"), str)
            or not isinstance(account.get("password_hash"), str)
        ):
            raise ValueError("Teacher account entries must contain salt and password_hash")
    return teachers
