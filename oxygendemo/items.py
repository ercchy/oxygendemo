"""
Oxygendemo model.
"""
from scrapy import Item
from scrapy import Field


class OxygendemoItem(Item):
    code = Field()
    price = Field()
    link = Field()
    designer = Field()
    name = Field()
    description = Field()
    images = Field()
    sale_discount = Field()
    stock_status = Field()
    type = Field()
    gender = Field()
    color = Field()
    raw_color = Field()

