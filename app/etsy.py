import re

from app import etsy_api


class EtsyListing(object):
    def __init__(self):
        raise NotImplementedError()


def get_etsy_listings_for_shop(shop_id):
    return etsy_api.get(f"shops/{shop_id}/listings/active")


def get_etsy_listing(listing_id):
    return etsy_api.get(f"listings/{listing_id}")


def get_all_etsy_categories():
    return etsy_api.get("/taxonomy/categories")


def get_etsy_listing_id_from_url(url):
    match = re.search("/listing/(\d+)/", url)

    if match:
        return int(match.group(1))

    return None
