"""SQLCipher AES-256 database at rest; fail closed on missing/wrong keys.

The key lives beside the database in an owner-only file, separate from the bridge token.
For a legacy SQLite file, export into a verified encrypted temporary file then atomically
replace the original. Never rewrite the only source file before validation.
"""
import os
import re
import secrets
import sqlite3 as plain_sqlite3
import tempfile
from pathlib import Path

import sqlcipher3

_SQLITE_HEADER = b"SQLite format 3\x00"
_KEY_RE = re.compile(r"[0-9a-f]{64}\Z")


def _read_key(path, create):
    path = Path(path)
    if path.exists():
        if path.is_symlink():
            raise RuntimeError("Database encryption key must not be a symlink.")
        key = path.read_text(encoding="ascii").strip()
        if not _KEY_RE.fullmatch(key):
            raise RuntimeError("Database key file is invalid; restore the original key.")
        return key
    if not create:
        raise RuntimeError("Encrypted database key is missing; refusing to create an empty database.")
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, "w", encoding="ascii") as file:
            key = secrets.token_hex(32)
            file.write(key + "\n")
            file.flush()
            os.fsync(file.fileno())
    except BaseException:
        path.unlink(missing_ok=True)
        raise
    return key


def _connect(path, key):
    conn = sqlcipher3.connect(str(path), check_same_thread=False)
    try:
        # SQLCipher raw 256-bit key (no password-based key stretching).
        conn.execute('PRAGMA key = "x' + "'" + key + "'" + '"')
        # Force early authentication; incorrect keys must never initialize tables.
        conn.execute("SELECT count(*) FROM sqlite_master").fetchone()
        return conn
    except BaseException:
        conn.close()
        raise


def _verify(path, key):
    conn = _connect(path, key)
    try:
        result = conn.execute("PRAGMA integrity_check").fetchone()
        if not result or result[0] != "ok":
            raise RuntimeError("Encrypted database integrity verification failed.")
        counts = tuple(conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                       for table in ("turns", "memories"))
        return counts
    finally:
        conn.close()


def _migrate(path, key):
    path = Path(path)
    plain = plain_sqlite3.connect(str(path))
    try:
        if plain.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise RuntimeError("Plaintext database failed integrity check; no migration.")
        # Merge possible WAL updates into the original file before SQLCipher export.
        plain.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        if plain.execute("PRAGMA journal_mode=DELETE").fetchone()[0].lower() != "delete":
            raise RuntimeError("Failed to close plaintext WAL; refusing migration.")
        source_counts = tuple(plain.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                              for table in ("turns", "memories"))
    finally:
        plain.close()

    fd, temporary = tempfile.mkstemp(prefix=".recall-encrypted-", suffix=".sqlite3",
                                     dir=str(path.parent))
    os.close(fd)
    os.unlink(temporary)  # ATTACH must create a new empty database.
    try:
        conn = sqlcipher3.connect(str(path))
        try:
            # Main connection is deliberately unkeyed: legacy plaintext SQLite.
            conn.execute('ATTACH DATABASE ? AS encrypted KEY "x' + "'" + key + "'" + '"',
                         (str(temporary),))
            try:
                conn.execute("SELECT sqlcipher_export('encrypted')").fetchone()
                conn.commit()
            finally:
                conn.execute("DETACH DATABASE encrypted")
        finally:
            conn.close()

        if _verify(temporary, key) != source_counts:
            raise RuntimeError("Encrypted copy row counts differ; original retained.")
        with open(temporary, "rb") as file:
            if file.read(16) == _SQLITE_HEADER:
                raise RuntimeError("Encryption did not alter the SQLite header.")
            os.fsync(file.fileno())
        os.chmod(temporary, 0o600)
        # Atomic replacement only after all checks; no plaintext backup is left in /data.
        os.replace(temporary, path)
        try:
            fd = os.open(str(path.parent), os.O_RDONLY)
            try:
                os.fsync(fd)
            finally:
                os.close(fd)
        except OSError:
            pass
    finally:
        Path(temporary).unlink(missing_ok=True)


def encrypted_connect(path):
    """Return a keyed DB-API connection; no fallback to plaintext or a new empty DB."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    key_path = path.with_suffix(".key")
    exists = path.exists() and path.stat().st_size > 0
    plain = False
    if exists:
        with path.open("rb") as file:
            plain = file.read(16) == _SQLITE_HEADER
    key = _read_key(key_path, create=not exists or plain)
    if plain:
        _migrate(path, key)
    # A new DB gets encrypted before the caller creates tables.
    db = _connect(path, key)
    db.execute("PRAGMA journal_mode=WAL")
    return db
