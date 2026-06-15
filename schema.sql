-- SQLite-схема для АИС «Электронная библиотека».
-- Файл рассчитан на учебный запуск с нуля: init_db.py пересоздаёт таблицы.

PRAGMA foreign_keys = OFF;
DROP TABLE IF EXISTS reviews;
DROP TABLE IF EXISTS covers;
DROP TABLE IF EXISTS book_genres;
DROP TABLE IF EXISTS books;
DROP TABLE IF EXISTS genres;
DROP TABLE IF EXISTS users;
DROP TABLE IF EXISTS roles;
DROP TABLE IF EXISTS review_statuses;
PRAGMA foreign_keys = ON;

-- Роли пользователей
CREATE TABLE roles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    description TEXT NOT NULL
);

-- Пользователи / читатели
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    login TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    last_name TEXT NOT NULL,
    first_name TEXT NOT NULL,
    middle_name TEXT,
    role_id INTEGER NOT NULL,
    FOREIGN KEY (role_id) REFERENCES roles(id)
);

-- Жанры
CREATE TABLE genres (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE
);

-- Книги
CREATE TABLE books (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    year INTEGER NOT NULL,
    publisher TEXT NOT NULL,
    author TEXT NOT NULL,
    pages INTEGER NOT NULL,
    CONSTRAINT chk_books_pages CHECK (pages > 0)
);

-- Связь книги-жанры: многие ко многим
CREATE TABLE book_genres (
    book_id INTEGER NOT NULL,
    genre_id INTEGER NOT NULL,
    PRIMARY KEY (book_id, genre_id),
    FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE,
    FOREIGN KEY (genre_id) REFERENCES genres(id) ON DELETE CASCADE
);

-- Обложки книг. У каждой книги должна быть обложка.
-- При одинаковом MD5 файл физически не дублируется: новые записи могут ссылаться на тот же filename.
CREATE TABLE covers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    filename TEXT NOT NULL,
    mime_type TEXT NOT NULL,
    md5_hash TEXT NOT NULL,
    book_id INTEGER NOT NULL UNIQUE,
    FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE
);

CREATE INDEX idx_covers_md5_hash ON covers(md5_hash);

-- Статусы рецензий, индивидуальный вариант 1
CREATE TABLE review_statuses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE
);

-- Рецензии
CREATE TABLE reviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    book_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    rating INTEGER NOT NULL,
    text TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    status_id INTEGER NOT NULL,
    FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (status_id) REFERENCES review_statuses(id),
    UNIQUE (book_id, user_id),
    CONSTRAINT chk_reviews_rating CHECK (rating BETWEEN 0 AND 5)
);

-- Начальные данные: роли
INSERT INTO roles (id, name, description) VALUES
(1, 'Администратор', 'Суперпользователь, имеет полный доступ к системе, в том числе к созданию и удалению книг'),
(2, 'Модератор', 'Может редактировать данные книг и производить модерацию рецензий'),
(3, 'Пользователь', 'Может оставлять рецензии');

-- Начальные данные: статусы рецензий
INSERT INTO review_statuses (id, name) VALUES
(1, 'На рассмотрении'),
(2, 'Одобрена'),
(3, 'Отклонена');

-- Начальные данные: жанры
INSERT INTO genres (name) VALUES
('Фантастика'),
('Детектив'),
('Роман'),
('Классика'),
('Фэнтези'),
('Научпоп'),
('История'),
('Поэзия'),
('Учебная литература'),
('Биография');
