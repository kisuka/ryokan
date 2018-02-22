import sys, scrapy, urlparse, os, io, json, requests, re
from scrapy.spiders import CrawlSpider, Rule
from scrapy.linkextractors import LinkExtractor
from scrapy.crawler import CrawlerProcess
from scrapy.http import Request
from pprint import pprint

class Ryokan(scrapy.Spider):
	name = 'ryokanspider'
	domain_url = 'https://www.japanican.com'
	allowed_domains = ["japanican.com"]
	all_hotels = []

	def start_requests(self):
		link = 'https://www.japanican.com/en/hotel/list/%s/?category=153'

		for x in range (1, 48):
			yield Request(link % ('%02d' % x), callback=self.inital_parse)

	def inital_parse(self, response):
		hotels = response.xpath("//a[text()='Details']/@href").extract()
		pages = response.xpath("//*[@class='list_pager__num']/a/@href").extract()

		if len(hotels) > 1:
			for hotel in hotels:
				yield Request(self.domain_url + str(hotel), callback=self.parse_hotel)

		if len(pages) > 1:
			for page in pages:
				yield Request(self.domain_url + str(page), callback=self.inital_parse)

	def parse_hotel(self, response):
		parsed = urlparse.urlparse(response.url)
		unique_id = str(parsed.path.split("/")[-2:][0])
		photos = []

		form_data = {"JsonParam": json.dumps({"chikuShisetsu":unique_id,"imageSearchType":"hotel","prevDispImageList":["","",""]}), "SiteType": "1"}
		r = requests.post("https://www.japanican.com/Service/Common/SearchHotelTourImage.ashx", data=form_data)
		images = json.loads(r.content)

		for image in images['ThumbsImageList']:
			photos.append(image['SsizeImageUrl'].replace("/S/","/XL/"))

		prefecture = response.xpath("//*[@id='mainform']/div[5]/div[1]/ul/li[3]/a/text()").extract()

		hotel = [{
			"en_title": response.xpath("//h1[@class='hotelinfo__name']/text()").extract()[0],
			"ja_title": response.xpath("//h1[@class='hotelinfo__name']/span/text()").extract()[0],
			"region": self.get_region(urlparse.parse_qs(parsed.query)['ar'][0]),
			"prefecture": re.sub("[^a-zA-Z]+", "", prefecture[0]),
			"address": response.xpath("//p[@class='hotelinfo__access']/a/text()").extract()[0],
			"features": response.xpath("//div[@class='categoryicon']/ul/li/text()").extract(),
			"built": response.xpath("//div[@id='hotel_contents_0_hotel_main_1_BuildingInfoHead']/table/tr[2]/td[2]/text()").extract()[0],
			"images": photos,
		}]

		self.all_hotels.extend(hotel)

	def get_region(self, area):
		if int(area) == 1:
			return 'Hokkaido'
		elif int(area) < 8:
			return 'Tohoku'
		elif int(area) < 15:
			return 'Kanto'
		elif int(area) < 24:
			return 'Chubu'
		elif int(area) < 31:
			return 'Kansai'
		elif int(area) < 36:
			return 'Chugoku'
		elif int(area) < 40:
			return 'Shikoku'
		elif int(area) < 47:
			return 'Kyushu'
		else:
			return 'Okinawa'

	def close(self, reason):
		with io.open(os.path.dirname(os.path.abspath(__file__))+'/ryokans.json', 'w', encoding='utf-8') as f:
			f.write(unicode(json.dumps(self.all_hotels, ensure_ascii=False)))

process = CrawlerProcess({'USER_AGENT': 'Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 5.1)'})
process.crawl(Ryokan)
process.start()