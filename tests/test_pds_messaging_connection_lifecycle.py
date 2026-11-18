"""SQLite connections for consent and approval workflows must close on all exits.

sqlite3.Connection.__exit__ only commits/rolls back; it does *not* close.
Long-lived request workers must not retain handles or WAL readers.
"""
import sqlite3
from types import SimpleNamespace

import pytest

from app.services import moses_pds_twilio, pds_schedule_notifications, pds_sms_consent


def _request(tmp_path):
    return SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(data_dir=str(tmp_path))))


@pytest.mark.parametrize('factory', [
    lambda folder: pds_sms_consent._connect(folder),
    lambda folder: moses_pds_twilio._db(_request(folder)),
    lambda folder: pds_schedule_notifications._db(_request(folder)),
])
def test_messaging_sqlite_connection_closed_after_success(tmp_path, factory):
    with factory(tmp_path) as connection:
        assert connection.execute('SELECT 1').fetchone()[0] == 1
    with pytest.raises(sqlite3.ProgrammingError, match='closed'):
        connection.execute('SELECT 1')


@pytest.mark.parametrize('factory', [
    lambda folder: pds_sms_consent._connect(folder),
    lambda folder: moses_pds_twilio._db(_request(folder)),
    lambda folder: pds_schedule_notifications._db(_request(folder)),
])
def test_messaging_sqlite_rolls_back_and_closes_on_error(tmp_path, factory):
    with pytest.raises(RuntimeError):
        with factory(tmp_path) as connection:
            connection.execute('CREATE TABLE IF NOT EXISTS temporary_probe (value TEXT)')
            connection.execute("INSERT INTO temporary_probe VALUES ('discard')")
            raise RuntimeError('simulated request failure')
    with pytest.raises(sqlite3.ProgrammingError, match='closed'):
        connection.execute('SELECT 1')
    with factory(tmp_path) as retry:
        assert retry.execute('SELECT COUNT(*) FROM temporary_probe').fetchone()[0] == 0
