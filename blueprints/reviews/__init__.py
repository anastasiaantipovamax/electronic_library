from flask import (Blueprint, abort, current_app, flash, redirect,
                   render_template, request, url_for)
from flask_login import current_user, login_required

from extensions import mysql
from filters import sanitize_markdown_source

reviews_bp = Blueprint('reviews', __name__)

RATINGS = [
    (5, 'отлично'),
    (4, 'хорошо'),
    (3, 'удовлетворительно'),
    (2, 'неудовлетворительно'),
    (1, 'плохо'),
    (0, 'ужасно'),
]


# ─── НАПИСАТЬ РЕЦЕНЗИЮ ─────────────────────────────────────────────────────────

@reviews_bp.route('/books/<int:book_id>/reviews/add', methods=['GET', 'POST'])
@login_required
def add(book_id):
    # Рецензии разрешены трём ролям из задания:
    # «Пользователь», «Модератор», «Администратор».
    # Новая рецензия любой из этих ролей всё равно получает статус «На рассмотрении».
    if not current_user.can_write_review:
        flash('У вас недостаточно прав для выполнения данного действия', 'danger')
        return redirect(url_for('books.index'))

    cursor = mysql.connection.cursor()
    cursor.execute('SELECT id, title FROM books WHERE id = %s', (book_id,))
    book = cursor.fetchone()
    if not book:
        cursor.close()
        abort(404)

    cursor.execute(
        'SELECT id FROM reviews WHERE book_id = %s AND user_id = %s',
        (book_id, current_user.id)
    )
    if cursor.fetchone():
        flash('Вы уже оставляли рецензию на эту книгу', 'warning')
        cursor.close()
        return redirect(url_for('books.view', book_id=book_id))
    cursor.close()

    form_data = {'rating': 5, 'text': ''}

    if request.method == 'POST':
        rating = request.form.get('rating', type=int)
        raw_text = request.form.get('text', '').strip()
        form_data = {'rating': rating, 'text': raw_text}

        errors = []
        if rating not in [0, 1, 2, 3, 4, 5]:
            errors.append('Выберите корректную оценку.')
        if not raw_text:
            errors.append('Введите текст рецензии.')

        if errors:
            for error in errors:
                flash(error, 'danger')
            flash('При сохранении рецензии возникла ошибка', 'danger')
            return render_template('reviews/add.html', book=book, ratings=RATINGS, form_data=form_data)

        text = sanitize_markdown_source(raw_text)

        try:
            cursor = mysql.connection.cursor()
            cursor.execute('''
                INSERT INTO reviews (book_id, user_id, rating, text, status_id)
                VALUES (%s, %s, %s, %s, 1)
            ''', (book_id, current_user.id, rating, text))
            mysql.connection.commit()
            cursor.close()
            flash('Рецензия отправлена на модерацию', 'success')
            return redirect(url_for('books.view', book_id=book_id))
        except Exception:
            mysql.connection.rollback()
            flash('При сохранении рецензии возникла ошибка', 'danger')

    return render_template('reviews/add.html', book=book, ratings=RATINGS, form_data=form_data)


# ─── МОИ РЕЦЕНЗИИ, ТОЛЬКО ДЛЯ РОЛИ «ПОЛЬЗОВАТЕЛЬ» ────────────────────────────

@reviews_bp.route('/my-reviews')
@login_required
def my_reviews():
    if not current_user.is_user:
        flash('У вас недостаточно прав для выполнения данного действия', 'danger')
        return redirect(url_for('books.index'))

    cursor = mysql.connection.cursor()
    cursor.execute('''
        SELECT r.*, b.title AS book_title, rs.name AS status_name
        FROM reviews r
        JOIN books b ON r.book_id = b.id
        JOIN review_statuses rs ON r.status_id = rs.id
        WHERE r.user_id = %s
        ORDER BY r.created_at DESC
    ''', (current_user.id,))
    reviews = cursor.fetchall()
    cursor.close()
    return render_template('reviews/my_reviews.html', reviews=reviews)


# ─── МОДЕРАЦИЯ РЕЦЕНЗИЙ: МОДЕРАТОР И АДМИНИСТРАТОР ───────────────────────────

@reviews_bp.route('/moderation')
@login_required
def moderation():
    if not (current_user.is_moderator or current_user.is_admin):
        flash('У вас недостаточно прав для выполнения данного действия', 'danger')
        return redirect(url_for('books.index'))

    page = max(request.args.get('page', 1, type=int), 1)
    per_page = current_app.config['REVIEWS_PER_PAGE']
    offset = (page - 1) * per_page

    cursor = mysql.connection.cursor()
    cursor.execute('SELECT COUNT(*) AS cnt FROM reviews WHERE status_id = 1')
    total = cursor.fetchone()['cnt']

    cursor.execute('''
        SELECT r.id, r.created_at, r.rating,
               b.title AS book_title, b.id AS book_id,
               u.first_name, u.last_name, u.middle_name
        FROM reviews r
        JOIN books b ON r.book_id = b.id
        JOIN users u ON r.user_id = u.id
        WHERE r.status_id = 1
        ORDER BY r.created_at ASC
        LIMIT %s OFFSET %s
    ''', (per_page, offset))
    reviews = cursor.fetchall()
    cursor.close()

    total_pages = (total + per_page - 1) // per_page if total else 1
    if page > total_pages:
        return redirect(url_for('reviews.moderation', page=total_pages))

    return render_template('reviews/moderation.html', reviews=reviews, page=page, total_pages=total_pages)


@reviews_bp.route('/moderation/<int:review_id>', methods=['GET', 'POST'])
@login_required
def moderate_review(review_id):
    if not (current_user.is_moderator or current_user.is_admin):
        flash('У вас недостаточно прав для выполнения данного действия', 'danger')
        return redirect(url_for('books.index'))

    cursor = mysql.connection.cursor()
    cursor.execute('''
        SELECT r.*, b.title AS book_title,
               u.first_name, u.last_name, u.middle_name,
               rs.name AS status_name
        FROM reviews r
        JOIN books b ON r.book_id = b.id
        JOIN users u ON r.user_id = u.id
        JOIN review_statuses rs ON r.status_id = rs.id
        WHERE r.id = %s
    ''', (review_id,))
    review = cursor.fetchone()
    if not review:
        cursor.close()
        abort(404)
    cursor.close()

    if request.method == 'POST':
        action = request.form.get('action')
        if action not in ('approve', 'reject'):
            flash('Некорректное действие модерации', 'danger')
            return redirect(url_for('reviews.moderation'))

        status_id = 2 if action == 'approve' else 3
        cursor = mysql.connection.cursor()
        cursor.execute('UPDATE reviews SET status_id = %s WHERE id = %s', (status_id, review_id))
        mysql.connection.commit()
        cursor.close()

        flash('Рецензия одобрена' if action == 'approve' else 'Рецензия отклонена', 'success')
        return redirect(url_for('reviews.moderation'))

    return render_template('reviews/moderate_review.html', review=review, ratings=RATINGS)
