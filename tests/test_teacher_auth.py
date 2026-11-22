import json
from http.cookies import SimpleCookie
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from fastapi import HTTPException, Response
from starlette.requests import Request

import src.app as app_module
from src.teacher_auth import password_hash


def make_request(token: str | None = None) -> Request:
    headers = []
    if token:
        headers.append(
            (b"cookie", f"{app_module.SESSION_COOKIE}={token}".encode("ascii"))
        )
    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/",
            "headers": headers,
            "query_string": b"",
            "server": ("testserver", 80),
            "client": ("testclient", 50000),
            "scheme": "http",
            "root_path": "",
            "http_version": "1.1",
        }
    )


class TeacherAuthTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.credentials_file = Path(self.temp_dir.name) / "teachers.json"
        salt = b"0123456789abcdef"
        self.credentials_file.write_text(
            json.dumps(
                {
                    "teachers": {
                        "teacher": {
                            "salt": salt.hex(),
                            "password_hash": password_hash(
                                "correct horse battery", salt
                            ).hex(),
                        }
                    }
                }
            ),
            encoding="utf-8",
        )
        self.original_activities = {
            name: {**activity, "participants": activity["participants"].copy()}
            for name, activity in app_module.activities.items()
        }
        app_module.sessions.clear()
        self.credentials_patch = patch.object(
            app_module, "TEACHERS_FILE", self.credentials_file
        )
        self.credentials_patch.start()

    def tearDown(self):
        app_module.activities.clear()
        app_module.activities.update(self.original_activities)
        app_module.sessions.clear()
        self.credentials_patch.stop()
        self.temp_dir.cleanup()

    def login(self) -> str:
        response = Response()
        app_module.login(
            app_module.TeacherCredentials(
                username="teacher",
                password="correct horse battery",
            ),
            make_request(),
            response,
        )
        cookie = SimpleCookie()
        cookie.load(response.headers["set-cookie"])
        return cookie[app_module.SESSION_COOKIE].value

    def test_registration_requires_teacher_session(self):
        with self.assertRaises(HTTPException) as error:
            app_module.signup_for_activity(
                "Chess Club", "new@mergington.edu", make_request()
            )
        self.assertEqual(error.exception.status_code, 401)
        with self.assertRaises(HTTPException) as error:
            app_module.unregister_from_activity(
                "Chess Club", "michael@mergington.edu", make_request()
            )
        self.assertEqual(error.exception.status_code, 401)

    def test_teacher_can_register_and_unregister_after_login(self):
        request = make_request(self.login())
        self.assertEqual(
            app_module.get_current_teacher(request),
            {"username": "teacher"},
        )

        app_module.signup_for_activity("Chess Club", "new@mergington.edu", request)
        self.assertIn(
            "new@mergington.edu",
            app_module.activities["Chess Club"]["participants"],
        )
        app_module.unregister_from_activity(
            "Chess Club", "new@mergington.edu", request
        )
        self.assertNotIn(
            "new@mergington.edu",
            app_module.activities["Chess Club"]["participants"],
        )

    def test_missing_teacher_configuration_disables_login(self):
        self.credentials_file.unlink()
        with self.assertRaises(HTTPException) as error:
            app_module.login(
                app_module.TeacherCredentials(username="teacher", password="password"),
                make_request(),
                Response(),
            )
        self.assertEqual(error.exception.status_code, 503)

    def test_invalid_password_is_rejected(self):
        with self.assertRaises(HTTPException) as error:
            app_module.login(
                app_module.TeacherCredentials(username="teacher", password="incorrect"),
                make_request(),
                Response(),
            )
        self.assertEqual(error.exception.status_code, 401)


if __name__ == "__main__":
    unittest.main()
