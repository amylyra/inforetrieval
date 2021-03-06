# -*- coding: utf-8 -*-

"""Beautylish Products Spider"""

# Imports =====================================================================

import json
import base64
import urllib
import scrapy

from beautylish.items import ProductItem, ReviewItem, ReviewerItem
from beautylish.loaders import ProductItemLoader, ReviewItemLoader, ReviewerItemLoader

# Spider ======================================================================

class BeautylishProductsSpider(scrapy.Spider):
    """Beautylish Products Spider"""

    name = "products"
    allowed_domains = ['beautylish.com']
    start_urls = ['https://www.beautylish.com/shop/browse']

    # -------------------------------------------------------------------------

    def parse(self, response):
        """Extract product links, follow them and go to next page if exists"""
        products = response.xpath('//a[@class="tile"]')
        for product in products:
            href = product.xpath('@href').extract_first()
            url = response.urljoin(href)
            yield scrapy.Request(url, callback=self.parse_product)
            
        # Follow next page if it exists
        next_page = response.xpath('//span[@class="pager_next"]/a')
        if next_page:
            href = next_page.xpath('@href').extract_first()
            url = response.urljoin(href)
            yield scrapy.Request(url)
        
    # -------------------------------------------------------------------------
    
    def parse_product(self, response):
        """Extract product details"""
        encoded = response.xpath('//script').re_first('window.scriptCtx = "([^"]+)"')
        decoded = base64.b64decode(encoded)
        data = json.loads(decoded)
        
        product_loader = ProductItemLoader(ProductItem(), response)
        product_loader.add_xpath('gtin', '//span[@itemprop="gtin13"]')
        product_loader.add_xpath('name', '//h1[@itemprop="name"]')
        product_loader.add_xpath('brandLogo', '//h3[@itemprop="brand"]/link[@itemprop="logo"]/@href')
        product_loader.add_xpath('brand', '//h3[@itemprop="brand"]/a[@itemprop="name"]')
        product_loader.add_xpath('category', '//ul[@itemprop="breadcrumb"]/li')
        product_loader.add_xpath('rating', '//meta[@itemprop="ratingValue"]/@content')
        product_loader.add_xpath('reviewCount', '//meta[@itemprop="reviewCount"]/@content')
        product_loader.add_xpath('priceCurrency', '//meta[@itemprop="priceCurrency"]/@content')
        product_loader.add_xpath('price', '//div[@itemprop="price"]')
        product_loader.add_xpath('image', '//img[@itemprop="image"]/@src')
        product_loader.add_xpath('ingredients', '//div[@id="accord-ingredients"]')
        product_loader.add_xpath('availability', '//link[@itemprop="availability"]/@href')
        product_loader.add_xpath('shipping', '//span[@class="img"][span[contains(@class, "shipIcon_time")]]/following-sibling::div[@class="body"]')
        product_loader.add_xpath('returnPolicy', '//span[@class="img"][span[contains(@class, "shipIcon_returns")]]/following-sibling::div[@class="body"]')
        product_loader.add_xpath('description', '//div[@id="desc-accord-content"]')
        product_loader.add_value('url', response.url)
        product = product_loader.load_item()
        product['reviews'] = []
        
        # Extract reviews if any, otherwise yield collected data
        if product['reviewCount'] > 0:
            cipherid = data['ProductApp']['product']['cipheredId']
            url = self.build_review_url(cipherid)
            yield scrapy.Request(
                url, 
                callback=self.parse_reviews, 
                meta={
                    'product': product,
                    'cipherid': cipherid,
                }
            )
        else:
            yield product
        
    # -------------------------------------------------------------------------

    def parse_reviews(self, response):
        """Extract reviews data"""
        product = response.meta['product']
        cipherid = response.meta['cipherid']
        reviews = json.loads(response.body)
        if len(reviews) > 0:
            for each in reviews:
                # Extract review information
                review_loader = ReviewItemLoader(ReviewItem())
                review_loader.add_value('title', each['shortText'])
                review_loader.add_value('description', each['text'])
                review_loader.add_value('rating', each['rating'])
                review_loader.add_value('helpfulCount', each['likesCount'])
                review_loader.add_value('reviewImage', each['images'][0]['clUrl'] if len(each['images']) > 0 else None)
                review_loader.add_value('datePublished', each['isoDate'])
                review = review_loader.load_item()
                
                # Extract reviewer information
                reviewer_loader = ReviewerItemLoader(ReviewerItem())
                reviewer_loader.add_value('name', each['userDisplayName'])
                reviewer_loader.add_value('profileUrl', each['userUrl'])
                reviewer = reviewer_loader.load_item()
                
                review['reviewer'] = reviewer
                product['reviews'].append(review)
                
            limit = 20
            offset = response.meta.get('offset', 0) + limit
            url = self.build_review_url(cipherid, offset)
            yield scrapy.Request(
                url, 
                callback=self.parse_reviews, 
                meta={
                    'product': product,
                    'cipherid': cipherid,
                    'offset': offset,
                }
            )
        else:
            # No more reviews, yield the collected data
            yield product
        
    # -------------------------------------------------------------------------
    
    def build_review_url(self, cipherid, offset=0, limit=20):
        """Build review url from cipherid"""
        base_url = "https://www.beautylish.com/rest/reviews/p-{cipherid}".format(cipherid=cipherid)
        params = {
            'offset': offset,
            'limit': limit,
            'sort': 'helpful'
        }
        query = urllib.urlencode(params)
        url = '{base_url}?{query}'.format(base_url=base_url, query=query)
        return url

# END =========================================================================
