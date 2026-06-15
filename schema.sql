-- Полная схема БД для АИС «Электронная библиотека».
-- Файл рассчитан на учебный запуск с нуля: init_db.py пересоздаёт таблицы.

SET FOREIGN_KEY_CHECKS = 0;
DROP TABLE IF EXISTS reviews;
DROP TABLE IF EXISTS covers;
DROP TABLE IF EXISTS book_genres;
DROP TABLE IF EXISTS books;
DROP TABLE IF EXISTS genres;
DROP TABLE IF EXISTS users;
DROP TABLE IF EXISTS roles;
DROP TABLE IF EXISTS review_statuses;
SET FOREIGN_KEY_CHECKS = 1;

-- Роли пользователей
CREATE TABLE roles (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE,
    description TEXT NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Пользователи / читатели
CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    login VARCHAR(100) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    first_name VARCHAR(100) NOT NULL,
    middle_name VARCHAR(100),
    role_id INT NOT NULL,
    FOREIGN KEY (role_id) REFERENCES roles(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Жанры
CREATE TABLE genres (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Книги
CREATE TABLE books (
    id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    year YEAR NOT NULL,
    publisher VARCHAR(255) NOT NULL,
    author VARCHAR(255) NOT NULL,
    pages INT NOT NULL,
    CONSTRAINT chk_books_pages CHECK (pages > 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Связь книги-жанры: многие ко многим
CREATE TABLE book_genres (
    book_id INT NOT NULL,
    genre_id INT NOT NULL,
    PRIMARY KEY (book_id, genre_id),
    FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE,
    FOREIGN KEY (genre_id) REFERENCES genres(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Обложки книг. У каждой книги должна быть обложка.
-- При одинаковом MD5 файл физически не дублируется: новые записи могут ссылаться на тот же filename.
CREATE TABLE covers (
    id INT AUTO_INCREMENT PRIMARY KEY,
    filename VARCHAR(255) NOT NULL,
    mime_type VARCHAR(100) NOT NULL,
    md5_hash VARCHAR(32) NOT NULL,
    book_id INT NOT NULL UNIQUE,
    FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE,
    INDEX idx_covers_md5_hash (md5_hash)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Статусы рецензий, индивидуальный вариант 1
CREATE TABLE review_statuses (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Рецензии
CREATE TABLE reviews (
    id INT AUTO_INCREMENT PRIMARY KEY,
    book_id INT NOT NULL,
    user_id INT NOT NULL,
    rating INT NOT NULL,
    text TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    status_id INT NOT NULL,
    FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (status_id) REFERENCES review_statuses(id),
    UNIQUE KEY uq_review_book_user (book_id, user_id),
    CONSTRAINT chk_reviews_rating CHECK (rating BETWEEN 0 AND 5)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

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
