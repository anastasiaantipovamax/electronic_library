from flask_login import UserMixin
from extensions import mysql


class User(UserMixin):
    def __init__(self, data):
        self.id = data['id']
        self.login = data['login']
        self.password_hash = data['password_hash']
        self.last_name = data['last_name']
        self.first_name = data['first_name']
        self.middle_name = data.get('middle_name')
        self.role_id = data['role_id']
        self.role_name = data.get('role_name', '')

    @property
    def full_name(self):
        parts = [self.last_name, self.first_name]
        if self.middle_name:
            parts.append(self.middle_name)
        return ' '.join(parts)

    @property
    def is_admin(self):
        return self.role_name == 'Администратор'

    @property
    def is_moderator(self):
        return self.role_name == 'Модератор'

    @property
    def is_user(self):
        return self.role_name == 'Пользователь'

    @property
    def can_write_review(self):
        # По заданию рецензию может написать любой аутентифицированный пользователь
        # с ролью «Пользователь», «Модератор» или «Администратор».
        return self.role_name in ('Пользователь', 'Модератор', 'Администратор')

    @staticmethod
    def get_by_id(user_id):
        cursor = mysql.connection.cursor()
        cursor.execute(
            '''SELECT u.*, r.name as role_name 
               FROM users u JOIN roles r ON u.role_id = r.id 
               WHERE u.id = %s''',
            (user_id,)
        )
        row = cursor.fetchone()
        cursor.close()
        return User(row) if row else None

    @staticmethod
    def get_by_login(login):
        cursor = mysql.connection.cursor()
        cursor.execute(
            '''SELECT u.*, r.name as role_name 
               FROM users u JOIN roles r ON u.role_id = r.id 
               WHERE u.login = %s''',
            (login,)
        )
        row = cursor.fetchone()
        cursor.close()
        return User(row) if row else None
