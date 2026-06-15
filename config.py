import os


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-prod')

    # SQLite. Работает на бесплатном PythonAnywhere без отдельного MySQL-тарифа.
    SQLITE_DB_PATH = os.environ.get(
        'SQLITE_DB_PATH',
        os.path.join(os.path.dirname(__file__), 'instance', 'library.sqlite3')
    )

    # Загрузка файлов
    UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'static', 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB

    BOOKS_PER_PAGE = 10
    REVIEWS_PER_PAGE = 10
