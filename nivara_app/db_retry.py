"""Retry SQLite operations when the DB is briefly locked (Windows + threaded runserver)."""
import time
import logging
from django.db import OperationalError, close_old_connections

logger = logging.getLogger(__name__)

MAX_ATTEMPTS = 30
BASE_SLEEP = 0.15


def sqlite_write(fn):
    """
    Run fn() (no args). Retries on sqlite locked/busy errors.
    """
    last_err = None
    for attempt in range(MAX_ATTEMPTS):
        close_old_connections()
        try:
            return fn()
        except OperationalError as e:
            last_err = e
            msg = str(e).lower()
            if "locked" not in msg and "busy" not in msg:
                raise
            if attempt == MAX_ATTEMPTS - 1:
                logger.warning("SQLite still locked after %s attempts", MAX_ATTEMPTS)
                raise
            time.sleep(BASE_SLEEP * (1.35**attempt))
    raise last_err
