from flask import Flask
from flask_login import LoginManager
from config import Config
from extensions import mysql
import os

login_manager = LoginManager()

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    mysql.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Для выполнения данного действия необходимо пройти процедуру аутентификации'
    login_manager.login_message_category = 'warning'

    from models import User

    @login_manager.user_loader
    def load_user(user_id):
        return User.get_by_id(int(user_id))

    # Регистрация Blueprint'ов
    from filters import register_filters
    register_filters(app)

    from blueprints.auth import auth_bp
    from blueprints.books import books_bp
    from blueprints.reviews import reviews_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(books_bp)
    app.register_blueprint(reviews_bp)

    # Создать папку для загрузок если нет
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)
