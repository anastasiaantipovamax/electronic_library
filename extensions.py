import os
import sqlite3
from datetime import datetime
from flask import current_app, g


class SQLiteCursor:
    """Небольшая обёртка, чтобы код проекта мог работать почти как с Flask-MySQLdb."""

    def __init__(self, cursor):
        self._cursor = cursor

    def execute(self, query, params=None):
        # В исходном проекте использовались MySQL-плейсхолдеры %s.
        # Для SQLite заменяем их на ?.
        query = query.replace('%s', '?')
        if params is None:
            params = []
        self._cursor.execute(query, params)
        return self

    def fetchone(self):
        row = self._cursor.fetchone()
        return self._convert_row(row) if row is not None else None

    def fetchall(self):
        return [self._convert_row(row) for row in self._cursor.fetchall()]

    @property
    def lastrowid(self):
        return self._cursor.lastrowid

    def close(self):
        self._cursor.close()

    @staticmethod
    def _convert_row(row):
        data = dict(row)
        for key, value in list(data.items()):
            if key.endswith('_at') and isinstance(value, str):
                try:
                    data[key] = datetime.fromisoformat(value)
                except ValueError:
                    pass
        return data


class SQLiteConnection:
    def __init__(self, connection):
        self._connection = connection

    def cursor(self):
        return SQLiteCursor(self._connection.cursor())

    def commit(self):
        self._connection.commit()

    def rollback(self):
        self._connection.rollback()


class SQLiteExtension:
    def init_app(self, app):
        app.config.setdefault(
            'SQLITE_DB_PATH',
            os.path.join(app.root_path, 'instance', 'library.sqlite3')
        )
        os.makedirs(os.path.dirname(app.config['SQLITE_DB_PATH']), exist_ok=True)
        app.teardown_appcontext(self._close_connection)

    @property
    def connection(self):
        return SQLiteConnection(self._get_connection())

    def _get_connection(self):
        if 'sqlite_db' not in g:
            db_path = current_app.config['SQLITE_DB_PATH']
            os.makedirs(os.path.dirname(db_path), exist_ok=True)
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            conn.execute('PRAGMA foreign_keys = ON')

            # SQLite по умолчанию плохо сравнивает русские буквы без учёта регистра.
            # Поэтому добавляем свою SQL-функцию для поиска: регистр не важен,
            # а буквы «ё» и «е» считаются одинаковыми.
            conn.create_function('SEARCH_NORM', 1, self._search_norm)

            g.sqlite_db = conn
        return g.sqlite_db


    @staticmethod
    def _search_norm(value):
        if value is None:
            return ''
        return str(value).casefold().replace('ё', 'е')

    @staticmethod
    def _close_connection(exception=None):
        conn = g.pop('sqlite_db', None)
        if conn is not None:
            conn.close()


# Имя mysql оставлено специально, чтобы минимально менять остальной код проекта.
# Фактически здесь используется SQLite.
mysql = SQLiteExtension()
