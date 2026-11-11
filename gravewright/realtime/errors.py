"""Recognize recoverable SQLite contention without hiding other database faults."""

import sqlite3

from django.db import connection


def database_busy(error):
    cause = error.__cause__
    code = getattr(cause, 'sqlite_errorcode', None)
    if code is not None:
        return code & 255 in (sqlite3.SQLITE_BUSY, sqlite3.SQLITE_LOCKED)
    return connection.vendor == 'sqlite' and str(error).lower() in {
        'database is locked', 'database table is locked', 'database schema is locked',
    }
