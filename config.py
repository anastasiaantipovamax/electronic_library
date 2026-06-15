import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-prod')

    # MySQL
    MYSQL_HOST = os.environ.get('MYSQL_HOST', 'localhost')
    MYSQL_USER = os.environ.get('MYSQL_USER', 'library_user')
    MYSQL_PASSWORD = os.environ.get('MYSQL_PASSWORD', 'library_pass')
    MYSQL_DB = os.environ.get('MYSQL_DB', 'library_db')
    MYSQL_CURSORCLASS = 'DictCursor'

    # Загрузка файлов
    UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'static', 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB

    BOOKS_PER_PAGE = 10
    REVIEWS_PER_PAGE = 10
