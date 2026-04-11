"""
Serialize HTTP requests when using SQLite so only one thread touches the DB at a time.
Prevents "database is locked" on Windows with threaded runserver.
"""
import threading
from django.conf import settings

_sqlite_lock = threading.Lock()


class SqliteSerializeRequestsMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        eng = (settings.DATABASES.get("default") or {}).get("ENGINE", "")
        self._use_lock = "sqlite" in eng.lower()

    def __call__(self, request):
        if not self._use_lock:
            return self.get_response(request)
        with _sqlite_lock:
            return self.get_response(request)
