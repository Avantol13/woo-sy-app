from flask import Flask
from config import Config
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_bootstrap import Bootstrap
from flask_login import LoginManager

app = Flask(__name__)
app.config.from_object(Config)

bootstrap = Bootstrap(app)

db = SQLAlchemy(app)
migrate = Migrate(app, db)

login = LoginManager()
login.init_app(app)

from app import routes, models, errors
