import hashlib
import os
from functools import wraps

from flask import (Blueprint, abort, current_app, flash, redirect,
                   render_template, request, url_for)
from flask_login import current_user

from extensions import mysql
from filters import sanitize_markdown_source

books_bp = Blueprint('books', __name__)


# ─── ПРОВЕРКА ПРАВ ─────────────────────────────────────────────────────────────

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Для выполнения данного действия необходимо пройти процедуру аутентификации', 'warning')
            return redirect(url_for('auth.login', next=request.url))
        if not current_user.is_admin:
            flash('У вас недостаточно прав для выполнения данного действия', 'danger')
            return redirect(url_for('books.index'))
        return f(*args, **kwargs)
    return decorated


def admin_or_moderator_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Для выполнения данного действия необходимо пройти процедуру аутентификации', 'warning')
            return redirect(url_for('auth.login', next=request.url))
        if not (current_user.is_admin or current_user.is_moderator):
            flash('У вас недостаточно прав для выполнения данного действия', 'danger')
            return redirect(url_for('books.index'))
        return f(*args, **kwargs)
    return decorated


# ─── ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ──────────────────────────────────────────────────

def get_genres():
    cursor = mysql.connection.cursor()
    cursor.execute('SELECT id, name FROM genres ORDER BY name')
    genres = cursor.fetchall()
    cursor.close()
    return genres


def get_book_or_404(book_id):
    cursor = mysql.connection.cursor()
    cursor.execute('SELECT * FROM books WHERE id = %s', (book_id,))
    book = cursor.fetchone()
    cursor.close()
    if not book:
        abort(404)
    return book


def validate_book_form(is_edit=False):
    """Возвращает (errors, data). Проверяет обязательные поля задания."""
    title = request.form.get('title', '').strip()
    raw_description = request.form.get('description', '').strip()
    publisher = request.form.get('publisher', '').strip()
    author = request.form.get('author', '').strip()
    year_raw = request.form.get('year', '').strip()
    pages_raw = request.form.get('pages', '').strip()
    genre_ids = [gid for gid in request.form.getlist('genres') if gid.isdigit()]
    cover_file = request.files.get('cover')

    errors = []

    if not title:
        errors.append('Введите название книги.')
    if not raw_description:
        errors.append('Введите краткое описание книги.')
    if not publisher:
        errors.append('Введите издательство.')
    if not author:
        errors.append('Введите автора.')

    try:
        year = int(year_raw)
        if year < 1000 or year > 2099:
            errors.append('Год должен быть в диапазоне от 1000 до 2099.')
    except ValueError:
        year = None
        errors.append('Введите корректный год.')

    try:
        pages = int(pages_raw)
        if pages <= 0:
            errors.append('Объём книги должен быть положительным числом.')
    except ValueError:
        pages = None
        errors.append('Введите корректный объём книги в страницах.')

    if not genre_ids:
        errors.append('Выберите хотя бы один жанр.')

    if not is_edit:
        if not cover_file or not cover_file.filename:
            errors.append('Загрузите обложку книги.')
        elif not cover_file.mimetype.startswith('image/'):
            errors.append('Обложка должна быть изображением.')

    data = {
        'title': title,
        'description': sanitize_markdown_source(raw_description),
        'raw_description': raw_description,
        'year': year,
        'publisher': publisher,
        'author': author,
        'pages': pages,
        'genre_ids': [int(gid) for gid in genre_ids],
        'cover_file': cover_file,
    }
    return errors, data


def form_data_for_template(data):
    return {
        'title': data.get('title', ''),
        'description': data.get('raw_description', data.get('description', '')),
        'year': data.get('year') or '',
        'publisher': data.get('publisher', ''),
        'author': data.get('author', ''),
        'pages': data.get('pages') or '',
        'genre_ids': data.get('genre_ids', []),
    }


def create_cover_record(cursor, cover_file, book_id):
    """
    Создаёт запись в таблице covers для книги.
    Если файл с таким MD5 уже есть, новый файл не сохраняется, используется существующее filename.
    Возвращает (filename, data, should_write_file).
    """
    data = cover_file.read()
    md5_hash = hashlib.md5(data).hexdigest()
    mime_type = cover_file.mimetype
    extension = os.path.splitext(cover_file.filename)[1].lower()

    cursor.execute(
        'SELECT filename, mime_type FROM covers WHERE md5_hash = %s LIMIT 1',
        (md5_hash,)
    )
    existing = cursor.fetchone()

    if existing:
        filename = existing['filename']
        cursor.execute(
            '''INSERT INTO covers (filename, mime_type, md5_hash, book_id)
               VALUES (%s, %s, %s, %s)''',
            (filename, mime_type or existing['mime_type'], md5_hash, book_id)
        )
        return filename, data, False

    cursor.execute(
        '''INSERT INTO covers (filename, mime_type, md5_hash, book_id)
           VALUES (%s, %s, %s, %s)''',
        ('pending', mime_type, md5_hash, book_id)
    )
    cover_id = cursor.lastrowid
    filename = f'{cover_id}{extension or ".jpg"}'
    cursor.execute('UPDATE covers SET filename = %s WHERE id = %s', (filename, cover_id))
    return filename, data, True


def write_cover_file(filename, data):
    os.makedirs(current_app.config['UPLOAD_FOLDER'], exist_ok=True)
    filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
    if not os.path.exists(filepath):
        with open(filepath, 'wb') as file:
            file.write(data)


def remove_cover_file_if_unused(filename):
    if not filename:
        return
    cursor = mysql.connection.cursor()
    cursor.execute('SELECT COUNT(*) AS cnt FROM covers WHERE filename = %s', (filename,))
    is_used = cursor.fetchone()['cnt'] > 0
    cursor.close()
    if not is_used:
        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        if os.path.exists(filepath):
            os.remove(filepath)




def normalize_search_query(value):
    """Нормализация поиска: без учёта регистра и без различия е/ё."""
    return value.casefold().replace('ё', 'е')


# ─── ГЛАВНАЯ СТРАНИЦА / ПОИСК / ПАГИНАЦИЯ ─────────────────────────────────────

@books_bp.route('/')
def index():
    page = max(request.args.get('page', 1, type=int), 1)
    per_page = current_app.config['BOOKS_PER_PAGE']
    offset = (page - 1) * per_page
    search_query = request.args.get('q', '').strip()

    where_sql = ''
    where_params = []
    if search_query:
        # Поиск должен работать по части слова и без учёта заглавных/строчных букв,
        # в том числе для русских букв. Обычный SQLite LIKE корректно игнорирует
        # регистр только для латиницы, поэтому используем свою функцию SEARCH_NORM.
        like = f'%{normalize_search_query(search_query)}%'
        where_sql = '''
            WHERE SEARCH_NORM(b.title) LIKE %s
               OR SEARCH_NORM(b.author) LIKE %s
               OR SEARCH_NORM(b.publisher) LIKE %s
               OR SEARCH_NORM(b.description) LIKE %s
               OR EXISTS (
                    SELECT 1
                    FROM book_genres bg_search
                    JOIN genres g_search ON g_search.id = bg_search.genre_id
                    WHERE bg_search.book_id = b.id AND SEARCH_NORM(g_search.name) LIKE %s
               )
        '''
        where_params = [like, like, like, like, like]

    cursor = mysql.connection.cursor()

    cursor.execute(f'SELECT COUNT(*) AS cnt FROM books b {where_sql}', where_params)
    total = cursor.fetchone()['cnt']

    cursor.execute(f'''
        SELECT b.id, b.title, b.year, b.author,
               c.filename AS cover_filename,
               GROUP_CONCAT(DISTINCT g.name) AS genres,
               AVG(CASE WHEN r.status_id = 2 THEN r.rating END) AS avg_rating,
               COUNT(DISTINCT CASE WHEN r.status_id = 2 THEN r.id END) AS review_count
        FROM books b
        LEFT JOIN covers c ON c.book_id = b.id
        LEFT JOIN book_genres bg ON b.id = bg.book_id
        LEFT JOIN genres g ON bg.genre_id = g.id
        LEFT JOIN reviews r ON b.id = r.book_id
        {where_sql}
        GROUP BY b.id, b.title, b.year, b.author, c.filename
        ORDER BY b.year DESC, b.id DESC
        LIMIT %s OFFSET %s
    ''', where_params + [per_page, offset])
    books = cursor.fetchall()
    cursor.close()

    total_pages = (total + per_page - 1) // per_page if total else 1
    if page > total_pages and total_pages > 0:
        return redirect(url_for('books.index', page=total_pages, q=search_query))

    return render_template(
        'books/index.html',
        books=books,
        page=page,
        total_pages=total_pages,
        q=search_query,
        total=total,
    )


# ─── ПРОСМОТР КНИГИ ────────────────────────────────────────────────────────────

@books_bp.route('/books/<int:book_id>')
def view(book_id):
    cursor = mysql.connection.cursor()

    cursor.execute('''
        SELECT b.*, c.filename AS cover_filename
        FROM books b
        LEFT JOIN covers c ON c.book_id = b.id
        WHERE b.id = %s
    ''', (book_id,))
    book = cursor.fetchone()
    if not book:
        cursor.close()
        abort(404)

    cursor.execute('''
        SELECT g.name
        FROM genres g
        JOIN book_genres bg ON g.id = bg.genre_id
        WHERE bg.book_id = %s
        ORDER BY g.name
    ''', (book_id,))
    book['genres'] = [row['name'] for row in cursor.fetchall()]

    user_review = None
    if current_user.is_authenticated:
        cursor.execute('''
            SELECT r.*, rs.name AS status_name
            FROM reviews r
            JOIN review_statuses rs ON rs.id = r.status_id
            WHERE r.book_id = %s AND r.user_id = %s
        ''', (book_id, current_user.id))
        user_review = cursor.fetchone()

    review_params = [book_id]
    current_user_filter = ''
    if current_user.is_authenticated:
        current_user_filter = 'AND r.user_id <> %s'
        review_params.append(current_user.id)

    cursor.execute(f'''
        SELECT r.*, u.first_name, u.last_name, u.middle_name
        FROM reviews r
        JOIN users u ON r.user_id = u.id
        WHERE r.book_id = %s AND r.status_id = 2 {current_user_filter}
        ORDER BY r.created_at DESC
    ''', review_params)
    reviews = cursor.fetchall()

    cursor.execute('SELECT COUNT(*) AS cnt FROM reviews WHERE book_id = %s AND status_id = 2', (book_id,))
    approved_review_count = cursor.fetchone()['cnt']

    cursor.close()
    return render_template(
        'books/view.html',
        book=book,
        reviews=reviews,
        user_review=user_review,
        approved_review_count=approved_review_count,
    )


# ─── ДОБАВЛЕНИЕ КНИГИ ──────────────────────────────────────────────────────────

@books_bp.route('/books/add', methods=['GET', 'POST'])
@admin_required
def add():
    genres = get_genres()

    if request.method == 'POST':
        errors, data = validate_book_form(is_edit=False)
        if errors:
            for error in errors:
                flash(error, 'danger')
            flash('При сохранении данных возникла ошибка. Проверьте корректность введённых данных.', 'danger')
            return render_template('books/form.html', genres=genres, book=form_data_for_template(data), is_edit=False)

        cover_to_write = None
        try:
            cursor = mysql.connection.cursor()
            cursor.execute('''
                INSERT INTO books (title, description, year, publisher, author, pages)
                VALUES (%s, %s, %s, %s, %s, %s)
            ''', (data['title'], data['description'], data['year'], data['publisher'], data['author'], data['pages']))
            book_id = cursor.lastrowid

            for genre_id in data['genre_ids']:
                cursor.execute(
                    'INSERT INTO book_genres (book_id, genre_id) VALUES (%s, %s)',
                    (book_id, genre_id)
                )

            filename, file_data, should_write_file = create_cover_record(cursor, data['cover_file'], book_id)
            if should_write_file:
                cover_to_write = (filename, file_data)

            mysql.connection.commit()
            cursor.close()

            if cover_to_write:
                write_cover_file(*cover_to_write)

            flash('Книга успешно добавлена', 'success')
            return redirect(url_for('books.view', book_id=book_id))

        except Exception:
            mysql.connection.rollback()
            flash('При сохранении данных возникла ошибка. Проверьте корректность введённых данных.', 'danger')
            return render_template('books/form.html', genres=genres, book=form_data_for_template(data), is_edit=False)

    return render_template('books/form.html', genres=genres, book=None, is_edit=False)


# ─── РЕДАКТИРОВАНИЕ КНИГИ ──────────────────────────────────────────────────────

@books_bp.route('/books/<int:book_id>/edit', methods=['GET', 'POST'])
@admin_or_moderator_required
def edit(book_id):
    cursor = mysql.connection.cursor()
    cursor.execute('SELECT * FROM books WHERE id = %s', (book_id,))
    book = cursor.fetchone()
    if not book:
        cursor.close()
        abort(404)

    cursor.execute('SELECT genre_id FROM book_genres WHERE book_id = %s', (book_id,))
    book['genre_ids'] = [row['genre_id'] for row in cursor.fetchall()]
    cursor.close()

    genres = get_genres()

    if request.method == 'POST':
        errors, data = validate_book_form(is_edit=True)
        if errors:
            for error in errors:
                flash(error, 'danger')
            flash('При сохранении данных возникла ошибка. Проверьте корректность введённых данных.', 'danger')
            return render_template('books/form.html', genres=genres, book=form_data_for_template(data), is_edit=True)

        try:
            cursor = mysql.connection.cursor()
            cursor.execute('''
                UPDATE books
                SET title = %s, description = %s, year = %s,
                    publisher = %s, author = %s, pages = %s
                WHERE id = %s
            ''', (data['title'], data['description'], data['year'], data['publisher'], data['author'], data['pages'], book_id))

            cursor.execute('DELETE FROM book_genres WHERE book_id = %s', (book_id,))
            for genre_id in data['genre_ids']:
                cursor.execute(
                    'INSERT INTO book_genres (book_id, genre_id) VALUES (%s, %s)',
                    (book_id, genre_id)
                )

            mysql.connection.commit()
            cursor.close()
            flash('Книга успешно обновлена', 'success')
            return redirect(url_for('books.view', book_id=book_id))

        except Exception:
            mysql.connection.rollback()
            flash('При сохранении данных возникла ошибка. Проверьте корректность введённых данных.', 'danger')
            return render_template('books/form.html', genres=genres, book=form_data_for_template(data), is_edit=True)

    return render_template('books/form.html', genres=genres, book=book, is_edit=True)


# ─── УДАЛЕНИЕ КНИГИ ────────────────────────────────────────────────────────────

@books_bp.route('/books/<int:book_id>/delete', methods=['POST'])
@admin_required
def delete(book_id):
    cursor = mysql.connection.cursor()
    cursor.execute('''
        SELECT b.id, b.title, c.filename
        FROM books b
        LEFT JOIN covers c ON c.book_id = b.id
        WHERE b.id = %s
    ''', (book_id,))
    book = cursor.fetchone()
    if not book:
        cursor.close()
        abort(404)

    filename = book['filename']
    title = book['title']

    try:
        cursor.execute('DELETE FROM books WHERE id = %s', (book_id,))
        mysql.connection.commit()
        cursor.close()

        # Обложка, рецензии и связи книги-жанры удаляются через ON DELETE CASCADE.
        # Файл обложки удаляем из файловой системы только если он больше не используется.
        remove_cover_file_if_unused(filename)

        flash(f'Книга «{title}» успешно удалена', 'success')
    except Exception:
        mysql.connection.rollback()
        flash('Ошибка при удалении книги', 'danger')

    return redirect(url_for('books.index'))
