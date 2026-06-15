"""
Инициализация БД для проекта «Электронная библиотека».

Скрипт выполняет schema.sql, пересоздаёт таблицы и добавляет тестовых пользователей.
Запуск:
    python init_db.py
"""
from pathlib import Path

from werkzeug.security import generate_password_hash

from app import create_app
from extensions import mysql


def split_sql_statements(sql_text):
    """Удаляет однострочные комментарии и делит SQL на отдельные операторы."""
    cleaned_lines = []
    for line in sql_text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith('--'):
            continue
        cleaned_lines.append(line)
    cleaned_sql = '\n'.join(cleaned_lines)
    return [statement.strip() for statement in cleaned_sql.split(';') if statement.strip()]


app = create_app()

with app.app_context():
    schema_path = Path(__file__).with_name('schema.sql')
    sql = schema_path.read_text(encoding='utf-8')

    cursor = mysql.connection.cursor()

    for statement in split_sql_statements(sql):
        cursor.execute(statement)

    users = [
        ('admin', 'password123', 'Иванов', 'Иван', 'Иванович', 1),
        ('moder', 'password123', 'Петрова', 'Мария', 'Сергеевна', 2),
        ('user1', 'password123', 'Сидоров', 'Алексей', None, 3),
    ]

    for login, password, last_name, first_name, middle_name, role_id in users:
        cursor.execute(
            '''INSERT INTO users
               (login, password_hash, last_name, first_name, middle_name, role_id)
               VALUES (%s, %s, %s, %s, %s, %s)''',
            (login, generate_password_hash(password), last_name, first_name, middle_name, role_id)
        )
        print(f'Создан пользователь: {login} / {password}')

    mysql.connection.commit()
    cursor.close()
    print('✓ БД полностью инициализирована')
