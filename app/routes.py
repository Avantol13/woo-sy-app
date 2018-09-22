from app import app, db, etsy_api, wcapi
from app.forms import RegistrationForm, ListingFromEtsyForm
import flask
from flask import flash, redirect, render_template
import pprint
import requests
import re
from urllib.parse import urlparse
from urllib.parse import urljoin
from flask import request, url_for
from flask_login import current_user, login_user
from flask_login import logout_user
from app.models import User
from app.forms import LoginForm
from flask_login import login_required


def is_safe_url(target):
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))
    return test_url.scheme in ("http", "https") and ref_url.netloc == test_url.netloc


@app.route("/super_secret_login", methods=["GET", "POST"])
def login():

    if current_user.is_authenticated:
        return redirect(url_for("index"))
    # Here we use a class of some kind to represent and validate our
    # client-side form data. For example, WTForms is a library that will
    # handle this for us, and we use a custom LoginForm to validate.
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        print(user)
        print(form.username.data)
        print(form.password.data)
        if user is None or not user.check_password(form.password.data):
            flash("Invalid username or password")
            return redirect(url_for("login"))

        # Login and validate the user.
        # user should be an instance of your `User` class
        login_user(user, remember=form.remember_me.data)

        flask.flash("Logged in successfully.")

        next = flask.request.args.get("next")
        # is_safe_url should check if the url is safe for redirects.
        # See http://flask.pocoo.org/snippets/62/ for an example.
        if not is_safe_url(next):
            return flask.abort(400)

        return flask.redirect(next or flask.url_for("index"))
    return flask.render_template("login.html", form=form)


@app.route("/super_secret_register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("index"))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash("Congratulations, you are now a registered user!")
        return redirect(url_for("login"))
    return render_template("register.html", title="Register", form=form)


@app.route("/logout")
def logout():
    logout_user()
    return redirect(url_for("index"))


class Listing(object):
    def __init__(
        self,
        title,
        description,
        price,
        is_draft,
        categories,
        short_desciption=None,
        **kwargs,
    ):
        self.title = title
        self.description = description
        self.price = price
        self.is_draft = is_draft
        self.categories = categories
        self.short_desciption = short_desciption

    def get_woocommerce_product_data(self):
        if self.is_draft:
            status = "draft"
        else:
            status = "publish"

        # make it draft anyway
        status = "draft"

        categories = self._get_woocommerce_categories()

        data = {
            "name": self.title,
            "type": "simple",
            "regular_price": self.price,
            "status": status,
            "description": self.description,
            "categories": list(categories),
            "images": [
                {
                    "src": "http://demo.woothemes.com/woocommerce/wp-content/uploads/sites/56/2013/06/T_2_front.jpg",
                    "position": 0,
                }
            ],
        }

        return data

    def _get_woocommerce_categories(self):
        woo_categories = set()
        for category in self.categories:
            woo_categories.add({"id": 18})
        return woo_categories

    @classmethod
    def from_etsy_listing_response(cls, resp):
        results = resp.get("results", [])
        if len(results) != 1:
            raise Exception(
                f"Etsy response does not contain just ONE listing. Response: {resp}"
            )

        listing = results.pop()
        title = listing.get("title")
        description = listing.get("description")
        price = listing.get("price")
        is_draft = bool(listing.get("state") == "draft")
        category_path = listing.get("category_path")
        categories = Listing._get_categories_from_etsy_category_path(category_path)
        return cls(title, description, price, is_draft, categories)

    @staticmethod
    def _get_categories_from_etsy_category_path(category_path):
        """
        Etsy's top level cats:
        ['Accessories', 'Art', 'Bags_And_Purses',
        'Bath_And_Beauty', 'Books_And_Zines', 'Candles',
        'Ceramics_And_Pottery', 'Children', 'Clothing',
        'Crochet', 'Dolls_And_Miniatures',
        'Everything_Else', 'Furniture', 'Geekery',
        'Glass', 'Holidays', 'Housewares', 'Jewelry',
        'Knitting', 'Music', 'Needlecraft', 'Paper_Goods',
        'Patterns', 'Pets', 'Plants_And_Edibles', 'Quilts',
        'Supplies', 'Toys', 'Vintage', 'Weddings',
        'Woodworking']

        Examples form ls shop
        ['Accessories', 'Watch']
        ['Accessories', 'Hair']
        ['Jewelry', 'Brooch']
        ['Clothing', 'Women', 'Dress']
        ['Clothing', 'Women', 'Jacket']
        ['Clothing', 'Women', 'Sleepwear']
        """
        categories = []
        first_item = category_path.pop(0)
        if first_item == "Accessories" or first_item == "":
            categories.append("Accessories")
        elif first_item == "Clothing":
            second_item = category_path.pop(1)
            if second_item == "Dress":
                categories.append("Dress")
        return []


def create_woocommerce_product(data):
    return wcapi.post("products", data)


def get_etsy_listings_for_shop(shop_id):
    return etsy_api.get(f"shops/{shop_id}/listings/active")


def get_etsy_listing(listing_id):
    return etsy_api.get(f"listings/{listing_id}")


def get_all_categories():
    return etsy_api.get("/taxonomy/categories")


def get_etsy_listing_id_from_url(url):
    match = re.search("/listing/(\d+)/", url)

    if match:
        return int(match.group(1))

    return None


@app.route("/")
@app.route("/index")
def index():
    return ""


@app.route("/etsy", methods=["GET", "POST"])
# @login_required
def etsy():
    form = ListingFromEtsyForm()
    if form.validate_on_submit():
        etsy_url = form.etsy_url.data

        listing_id = get_etsy_listing_id_from_url(etsy_url)
        pprint.pprint(listing_id)

        # pprint.pprint(get_etsy_listings_for_shop(etsy_shop_id).json())
        etsy_listing = get_etsy_listing(listing_id).json()
        pprint.pprint(etsy_listing)

        listing = Listing.from_etsy_listing_response(etsy_listing)

        woo_listing_data = listing.get_woocommerce_product_data()
        pprint.pprint(woo_listing_data)

        response = create_woocommerce_product(woo_listing_data)
        pprint.pprint(response.text)

        flash(f"Listing created in WooCommerce from Etsy listing id {listing_id}!")
        return redirect(url_for("etsy"))
    return render_template("listing_from_etsy.html", title="Etsy Sync", form=form)
