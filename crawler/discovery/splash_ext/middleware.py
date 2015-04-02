# -*- coding: utf-8 -*-
from __future__ import absolute_import
import logging
from urlparse import urljoin
from urllib import urlencode
import json
from scrapy import log


class SplashMiddleware(object):
    """
    Scrapy downloader middleware that passes requests through Splash_
    when 'splash' Request.meta key is set.

    To enable the middleware add it to settings::

        DOWNLOADER_MIDDLEWARES = {
            'splash_mw.SplashMiddleware': 950,
        }

    and then use ``splash`` meta key to pass options::

        yield Request(url, self.parse_result, meta={'splash': {
            # use render.json options here
            'html': 1,
            'png': 1,
        }}

    The response

    .. _Splash: https://github.com/scrapinghub/splash

    """
    DEFAULT_SPLASH_URL = 'http://127.0.0.1:8050'
    SPLASH_EXTRA_TIMEOUT = 10
    RESPECT_SLOTS = True

    def __init__(self, crawler, splash_url):
        self.crawler = crawler
        self._splash_url = splash_url

    @classmethod
    def from_crawler(cls, crawler):
        url = crawler.settings.get('SPLASH_URL', cls.DEFAULT_SPLASH_URL)
        return cls(crawler, url)

    def splash_url(self, query, url, endpoint='render.json'):
        query = query.copy()
        query['url'] = url
        return urljoin(self._splash_url, endpoint) + '?' + urlencode(query)

    def process_request(self, request, spider):
        splash_options = request.meta.get('splash')
        if not splash_options:
            return

        if request.method != 'GET':
            log.msg("Only GET requests are supported by SplashMiddleware; %s will be handled without Splash" % request, logging.WARNING)
            return request

        for key, value in splash_options.items():
            if key.lower() == 'timeout':
                request.meta['download_timeout'] = max(
                    request.meta.get('download_timeout', 1e6),
                    float(value) + self.SPLASH_EXTRA_TIMEOUT
                )

        if self.RESPECT_SLOTS:
            # Use the same download slot to (sort of) respect download
            # delays and concurrency options.
            request.meta['download_slot'] = self._get_slot_key(request)

        del request.meta['splash']
        request.meta['_splash'] = True
        request.meta['_origin_url'] = request.url

        # FIXME: original HTTP headers are not respected.
        # To respect them changes to Splash are needed.
        request.headers = {}
        request._set_url(self.splash_url(splash_options, request.url))

        self.crawler.stats.inc_value('splash/request_count')

    def process_response(self, request, response, spider):
        if '_splash' in request.meta:
            response._set_url(request.meta['_origin_url'])
            data = json.loads(response.body, encoding='utf8')
            response.request = request
            response.meta['splash_response'] = data
            if 'html' in data:
                response._encoding = response.encoding
                response._set_body(data['html'])
                response._cached_ubody = None

            self.crawler.stats.inc_value('splash/response_count/%s' % response.status)
        return response

    def _get_slot_key(self, request_or_response):
        return self.crawler.engine.downloader._get_slot_key(request_or_response, None)
