import os
from flask import Flask
from config import Config
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_bootstrap import Bootstrap
from flask_login import LoginManager

from woocommerce import API
from etsy_py.api import EtsyAPI

app = Flask(__name__)
app.config.from_object(Config)

bootstrap = Bootstrap(app)

db = SQLAlchemy(app)
migrate = Migrate(app, db)

login = LoginManager()
login.init_app(app)

ETSY_SHOP_ID = os.environ.get("ETSY_SHOP_ID") or ""
etsy_api = EtsyAPI(api_key=os.environ.get("ETSY_API_KEY"))

wcapi = API(
    url=os.environ.get("WORDPRESS_URL"),
    consumer_key=os.environ.get("WORDPRESS_CUSTOMER_KEY"),
    consumer_secret=os.environ.get("WORDPRESS_CUSTOMER_SECRET"),
    wp_api=True,
    verify_ssl=True,
    version="wc/v1",
    timeout=15,
)


from app import routes, models, errors
