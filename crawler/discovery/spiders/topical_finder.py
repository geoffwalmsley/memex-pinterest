from ranker import Ranker
from crawler.discovery.items import WebpageItemLoader
from crawler.discovery.urlutils import (
    add_scheme_if_missing,
    get_domain,
    is_external_url
)
from website_finder import SplashSpiderBase

from scrapy.http import Request, TextResponse
from scrapy.contrib.linkextractors import LinkExtractor
from scrapy.utils.httpobj import urlparse_cached
from scrapy import log, signals
from scrapy.exceptions import DontCloseSpider

from datetime import datetime


class TopicalFinder(SplashSpiderBase):
    name = 'topical_finder'

    save_html = None
    use_splash = None

    def __init__(self, seed_urls=None, save_html=1, use_splash=0, screenshot_dir=None, op_time=10, **kwargs):
        '''
        Constructs spider instance from command=line or scrapyd daemon.

        :param seed_urls: Comma-separated list of URLs, if empty crawler will be following not crawled URLs from storage
        :param save_html: boolean 0/1
        :param use_splash: boolean 0/1
        :param screenshot_dir: used only when use_splash=1
        :param op_time: operating time in minutes, negative - don't use that constraint
        :param kwargs:
        :return:
        '''
        super(TopicalFinder, self).__init__(screenshot_dir=screenshot_dir, **kwargs)
        self.screenshot_dir = screenshot_dir
        if seed_urls:
            self.start_urls = [add_scheme_if_missing(url) for url in seed_urls.split(',')]
        self.ranker = Ranker.load()
        self.linkextractor = LinkExtractor()
        self.save_html = bool(save_html)
        self.use_splash = bool(use_splash)
        self.operating_time = int(op_time) * 60

        self.start_time = datetime.utcnow()
        self.finishing = False

    def start_requests(self):
        for url in self.start_urls:
            yield self.make_requests_from_url(url, is_seed=True)

    def make_requests_from_url(self, url, is_seed=False):
        if self.use_splash:
            r = self._splash_request(url)
        else:
            r = super(TopicalFinder, self).make_requests_from_url(url)
        r.meta['score'] = 0.0
        r.meta['is_seed'] = False

        if is_seed:
            r.meta['is_seed'] = True
            r.meta['score'] = 1.0  # setting maximum score value for seeds
        return r

    def set_crawler(self, crawler):
        super(TopicalFinder, self).set_crawler(crawler)
        self.crawler.signals.connect(self.spider_idle, signal=signals.spider_idle)

    def spider_idle(self):
        log.msg("Spider idle signal caught.")
        raise DontCloseSpider

    def parse(self, response):
        ld = self._load_webpage_item(response, is_seed=response.meta['is_seed'])
        if self.use_splash:
            self._process_splash_response(response, ld)
        yield ld.load_item()

        if self.finishing:
            return

        now = datetime.utcnow()
        if self.operating_time > 0 and (now - self.start_time).total_seconds() > self.operating_time:
            log.msg("Reached operating time constraint. Waiting for Scrapy queue to exhaust.")
            self.finishing = True
            self.crawler.stop()
            return

        if not isinstance(response, TextResponse):
            return

        body = response.body_as_unicode().strip().encode('utf8') or '<html/>'
        score = self.ranker.score_html(body)
        log.msg("TC: %s has score=%f" % (response.url, score), _level=log.DEBUG)
        if score > 0.5:
            for link in self.linkextractor.extract_links(response):
                if self.use_splash:
                    r = self._splash_request(url=link.url)
                else:
                    r = Request(url=link.url)

                external = is_external_url(response.url, link.url)
                depth = response.meta.get('link_depth', 0)
                r.meta.update({
                    'link': {
                        'url': link.url,
                        'text': link.text,
                        'fragment': link.fragment,
                        'nofollow': link.nofollow},
                    'link_depth': 0 if external else depth + 1,
                    'referrer_depth': depth,
                    'referrer_url': response.url,
                })

                url_parts = urlparse_cached(r)
                path_parts = url_parts.path.split('/')
                r.meta['score'] = 1.0 / len(path_parts)
                r.meta['is_seed'] = False
                yield r

    def _load_webpage_item(self, response, is_seed):
        depth = response.meta.get('link_depth', 0)
        ld = WebpageItemLoader(response=response)
        ld.add_value('url', response.url)
        ld.add_value('host', get_domain(response.url))
        ld.add_xpath('title', '//title/text()')
        ld.add_value('depth', depth)
        ld.add_value('total_depth', response.meta.get('depth'))
        ld.add_value('crawled_at', datetime.utcnow())
        ld.add_value('is_seed', is_seed)
        ld.add_value('crawler_score', response.meta['score'])

        if self.save_html:
            ld.add_value('html', response.body_as_unicode())

        if 'link' in response.meta:
            link = response.meta['link']
            ld.add_value('link_text', link['text'])
            ld.add_value('link_url', link['url'])
            ld.add_value('referrer_url', response.meta['referrer_url'])
            ld.add_value('referrer_depth', response.meta['referrer_depth'])
        return ld