"""
Oxygen spider v1.
"""
from decimal import Decimal
import pyquery
import logging

from scrapy import Request, FormRequest
from scrapy.spiders import Rule, CrawlSpider
from scrapy.linkextractors import LinkExtractor

from ..items import OxygendemoItem


class OxygenSpider(CrawlSpider):
	"""
	Crawls oxygenboutique.com for products and prices with special processing
	to set currency to USD.
	"""
	name = 'oxygendemo'
	allowed_domains = ['oxygenboutique.com']
	start_urls = [
		'http://www.oxygenboutique.com',
	]
	currency_url = "http://www.oxygenboutique.com/Currency.aspx"

	rules = [
		Rule(LinkExtractor(
			allow=['.*.aspx$'],
			deny=['.*(13|14|15|Lookbook).*aspx$'],
			restrict_xpaths=['//ul[@class="topnav"]']
		), follow=True),
		Rule(LinkExtractor(
			allow=['.*.aspx$'],
			restrict_xpaths=['//body[@class="product_page"]', '//div[@class="itm"]/div[@class="itm"]//a']
		), callback='parse_item')
	]

	def start_requests(self):
		"""
		Start processing pages with currency change to USD.
		"""
		self.log('start_requests', level=logging.INFO)
		yield Request(
			url=self.currency_url,
			callback=self.currency_form
		)

	def currency_form(self, response):
		"""
		Currency form viewed and change to USD posted.
		"""
		self.log('currency_form', level=logging.INFO)
		formdata = {
			'ddlCountry1': 'United States',
			'ddlCurrency': '503329C6-40CB-47E6-91D1-9F11AF63F706'
		}
		return FormRequest.from_response(response,
		                                 formdata=formdata,
		                                 callback=self.currency_changed)

	def currency_changed(self, response):
		"""
		Currency has been set to USD, regular processing of pages can commence.
		- ie. as it would be processed by CrawlSpider without
		  custom self.start_requests method
		"""
		self.log('currency_changed', level=logging.INFO)
		for start_url in self.start_urls:
			yield Request(url=start_url)

	def parse_item(self, response):
		"""
		Parses product pages.
		"""
		logging.info("Crawling: " + response.url)

		pq = pyquery.PyQuery(response.body)
		item = OxygendemoItem()

		# extracting the link
		link = response.url

		# extracting the designer
		designer = pq(pq('.brand_name a')).html().strip()

		# extracting the price and the discount percent
		price, sale_discount = get_price(pq)

		# extracting the name
		name = pq(pq('.right h2')).text().strip()

		# extracting the description
		description = pq(pq('meta[name="description"]')).attr('content').strip()

		# extract the slugified url from the page as a part of the code
		code = "oxygenboutique-" + pq(pq('form[name="aspnetForm"]')).attr('action').strip('/, .aspx')

		# extract all the images including thumbnails
		images = pq('#product-images #large-image img[src*="/GetImage/"], #product-images #thumbnails #thumbnails-container img')
		item_imgs = ['http://oxygenboutique.com' + pq(img).attr('src') for img in images]

		# get stock status
		stock_status = get_sizes(pq)

		item['designer'] = designer
		item['price'] = price
		item['link'] = link
		item['name'] = name
		item['code'] = code
		item['description'] = description
		item['images'] = item_imgs
		item['sale_discount'] = sale_discount
		item['stock_status'] = stock_status
		item['type'] = 'A'  # The site does not provide sufficient info to make a good guess
		item['raw_color'] = ''  # There is no color info about the item
		item['gender'] = 'F'  # The site is specialized for female items

		return item


def get_sizes(pq):
	"""
	Parses the available sizes for an item and wraps the info into dict.

	Returns:
	- dict which is carring values of 1 (out of stock) or 3 (in stock)
	  of a certain size (eg.{"XXL": 3, "L": 1})
	"""
	sizes = pq(pq("select[id*='Size']")).children()
	stock_status = {}
	for size in sizes[1:]:
		if pq(size).attr('disabled'):
			stock_status[pq(size).text().split(' ')[0]] = 1
		else:
			stock_status[pq(size).text()] = 3
	return stock_status


def get_price(pq):
	"""
	Parses the price out of a product page.

	It handles two use cases:
	- regular price
	- discounted price

	Returns:
	- tuple (price, discount in precentage)
	"""
	raw_price = pq(pq("span.price")).text().strip().split(' ')
	price = Decimal(0)
	discount = Decimal(0)
	if raw_price:
		if len(raw_price) == 3:
			price = Decimal(raw_price[1])
			discounted = raw_price[2]
			discount = (Decimal(price) - Decimal(discounted)) / Decimal(price)
		else:
			price = raw_price[0][1:]

	return price, discount

