from app import app, db
from app.forms import RegistrationForm, WoosyListingFromEtsyForm
import flask
import json
from app.wordpress import upload_image_from_url
from copy import copy
from flask import flash, redirect, render_template
from urllib.parse import urlparse
from urllib.parse import urljoin
from flask import request, url_for
from flask_login import current_user, login_user
from flask_login import logout_user
from app.models import User
from app.forms import LoginForm
from flask_login import login_required

from app.etsy import (
    get_etsy_listing_id_from_url,
    get_etsy_listing,
    get_etsy_listing_image_urls,
)
from app.woocommerce import WooCommerceProduct
from app.listing import WoosyListing, WoosyImage


def is_safe_url(target):
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))
    return test_url.scheme in ("http", "https") and ref_url.netloc == test_url.netloc


@app.route("/")
@app.route("/index")
def index():
    return render_template("index.html")


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
@login_required  # TODO remove to allow user registration by anyone
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


@app.route("/etsy", methods=["GET", "POST"])
@login_required
def etsy():
    form = WoosyListingFromEtsyForm()
    if form.validate_on_submit():
        etsy_url = form.etsy_url.data

        listing_id = get_etsy_listing_id_from_url(etsy_url)
        etsy_listing_response = get_etsy_listing(listing_id)
        woosy_listing = WoosyListing.from_etsy_listing_response(etsy_listing_response)

        # getting etsy images requires another API call
        etsy_image_urls = get_etsy_listing_image_urls(listing_id)

        # upload images to wordpress
        wordpress_imgs = []
        for img_url in etsy_image_urls:
            response = upload_image_from_url(img_url)
            wordpress_imgs.append(response)
            app.logger.debug("Wordpress Image Upload: " + str(response))

        # assume first pic returned is the main image
        main_image = None
        if wordpress_imgs:
            main_image = WoosyImage(wordpress_imgs.pop(0).get("url"))

        woosy_listing.main_image = main_image
        woosy_listing.other_images = [
            WoosyImage(img.get("url")) for img in wordpress_imgs
        ]

        app.logger.debug("Etsy resp: " + str(etsy_listing_response.json()))
        app.logger.debug("woosy_listing: " + str(json.loads(woosy_listing.to_json())))

        woo_listing_data = WooCommerceProduct.from_woosy_listing(woosy_listing)
        app.logger.debug(
            "WooCommerceProduct: " + str(json.loads(woo_listing_data.to_json()))
        )

        response = woo_listing_data.post()
        app.logger.debug("WooCommerce repsonse: " + str(response.text))

        flash(f"Product created in WooCommerce from Etsy listing ID: {listing_id}!")
        return redirect(url_for("etsy"))
    return render_template("listing_from_etsy.html", title="Etsy Sync", form=form)
