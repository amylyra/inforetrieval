# -*- coding: utf-8 -*-

"""EssentialNaturalOils Products Spider"""

# Imports =====================================================================

import re

import scrapy
from scrapy.spiders import CrawlSpider, Rule
from scrapy.linkextractors import LinkExtractor

from essentialnaturaloils.items import ProductItem, ReviewItem
from essentialnaturaloils.loaders import ProductItemLoader, ReviewItemLoader

# Spider ======================================================================

class EssentialNaturalOilsProductsSpider(CrawlSpider):
    """EssentialNaturalOils Products Spider"""

    name = "products"
    allowed_domains = ['essentialnaturaloils.com']
    start_urls = [
        'http://www.essentialnaturaloils.com/natural-essential-oils',
        'http://www.essentialnaturaloils.com/cold-pressed-carrier-oils',
        'http://www.essentialnaturaloils.com/super-exotic-aromatherapy-blends',
        'http://www.essentialnaturaloils.com/essential-oil-blends',
        'http://www.essentialnaturaloils.com/floral-absolutes',
        'http://www.essentialnaturaloils.com/fragrances',
        'http://www.essentialnaturaloils.com/floral-waxes',
        'http://www.essentialnaturaloils.com/oleoresin',
        'http://www.essentialnaturaloils.com/insect-repellents',
        'http://www.essentialnaturaloils.com/pain-relief-natural-oils',
        'http://www.essentialnaturaloils.com/oils-for-hair-health',
        'http://www.essentialnaturaloils.com/floral-waters',
        'http://www.essentialnaturaloils.com/exotic-dilutions',
        'http://www.essentialnaturaloils.com/bottels-droppers-essential-oil-diffuser',
        'http://www.essentialnaturaloils.com/index.php?route=product/category&path=83',
        'http://www.essentialnaturaloils.com/index.php?route=product/category&path=82',
        'http://www.essentialnaturaloils.com/herbal-extracts',
    ]
    rules = (
        # Parse product details
        Rule(
            LinkExtractor(restrict_css='#products .product-meta .name'),
            callback='parse_product',
        ),

        # Follow pagination
        Rule(LinkExtractor(restrict_css='.pagination')),
    )

    # -------------------------------------------------------------------------

    def parse_product(self, response):
        """Extract product details"""
        loader = ProductItemLoader(ProductItem(), response)
        loader.add_xpath('id', '//input[@name="product_id"]/@value')
        loader.add_css('name', '.title-product')
        loader.add_css('category', '.breadcrumb > li:not(:first-child) > a')
        loader.add_css('price', '#thisIsOriginal')
        loader.add_css('description', '#tab-description')
        loader.add_xpath('code', '//div[@class="description"]//b[.="Product Code:"]/following-sibling::text()')
        loader.add_xpath('availability', '//div[@class="description"]//b[.="Availability:"]/following-sibling::span')
        loader.add_xpath('options', '//select/option[position() > 1]')
        loader.add_css('image', '#image::attr(src)')
        loader.add_xpath('rating', 'count(//div[@class="review"]//i[@class="fa fa-star fa-stack-1x"])')
        loader.add_css('reviews_count', '.review', re='(\d+) reviews')
        loader.add_value('url', response.url)
        product = loader.load_item()

        if product['reviews_count'] > 0:
            reviews_url = response.urljoin(
                '/index.php?route=product/product/review&product_id={product_id}'
                .format(product_id=product['id'])
            )
            return scrapy.Request(
                reviews_url,
                callback=self.parse_reviews,
                meta=dict(product=product)
            )

        return product

    # -------------------------------------------------------------------------

    def parse_reviews(self, response):
        """Extract product reviews"""
        product = response.meta['product']
        product['reviews'] = []

        for review in response.css('.table'):
            loader = ReviewItemLoader(ReviewItem(), review)
            loader.add_xpath('name', 'tr[1]/td[1]')
            loader.add_xpath('date', 'tr[1]/td[2]')
            loader.add_xpath('text', 'tr[2]')
            loader.add_xpath('rating', 'count(tr[2]//i[@class="fa fa-star fa-stack-1x"])')

            review = loader.load_item()
            product['reviews'].append(review)

        return product

# END =========================================================================
