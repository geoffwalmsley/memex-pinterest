from __future__ import absolute_import

import sys
sys.path.append("../../../")
import requests
import os
import json
import base64
from hashlib import md5
import scrapy
from crawler.discovery.urlutils import (
    add_scheme_if_missing,
    is_external_url,
    get_domain,
)
from ui.mongoutils.memex_mongo_utils import MemexMongoUtils
from crawler.discovery.settings import SPLASH_URL
import grequests


class SplashGet(object):
    """Manually get a splash screenshot"""

    def __init__(self, screenshot_dir, which_collection = "crawl-data"):
        self.mmu = MemexMongoUtils(which_collection = which_collection)
        self.screenshot_dir = screenshot_dir

    def makedir(self, path):
        try:
            os.makedirs(path)
        except OSError:
            pass
    
    def splash_request(self, url):

        splash_response = requests.get(SPLASH_URL + '/render.json?url=%s&html=1&png=1&wait=2.0&width=640&height=480&timeout=60&images=0' % url)
        return splash_response

    def save_screenshot(self, prefix, data):
        png = base64.b64decode(data['png'])
        dirname = os.path.join(self.screenshot_dir, prefix)
        self.makedir(dirname)
    
        fn = os.path.join(dirname, md5(png).hexdigest() + '.png')
        print fn
        with open(fn, 'wb') as fp:
            fp.write(png)
        return fn

    def process_splash_response(self, url, splash_response):
        data = json.loads(splash_response.text, encoding='utf8')
    
        screenshot_path = self.save_screenshot(get_domain(url), data)
        html_rendered = data["html"]
        
        return screenshot_path, html_rendered

    def request_and_save(self, url):
        print "Getting screenshot for %s" % url
        splash_response = self.splash_request(url)
        screenshot_path, html_rendered = self.process_splash_response(url, splash_response)
        self.mmu.set_screenshot_path(url, screenshot_path)
        self.mmu.set_html_rendered(url, html_rendered)

    def resolve_images_by_host(self, host):
        url_dics = self.mmu.list_urls(host, limit=2000)
        for url_dic in url_dics:
            self.request_and_save(url_dic["url"])

    def resolve_images_by_url_match(self, match_term):
        url_dics = self.mmu.list_all_urls()
        for url_dic in url_dics:
            #get only if it doesn't have an existing screenshot            
            if "screenshot_path" not in url_dic:
                #!string matching for now, makes more sense as regex
                if match_term in url_dic["url"]:
                    self.request_and_save(url_dic["url"])

    def resolve_images_by_host_match(self, match_term):
        url_dics = self.mmu.list_all_urls()
        for url_dic in url_dics:
            #get only if it doesn't have an existing screenshot
            if "screenshot_path" not in url_dic:
                #!string matching for now, makes more sense as regex
                if match_term in url_dic["host"]:
                    self.request_and_save(url_dic["url"])

    def get_url_chunks(self, chunk_size):
        url_dics = self.mmu.list_all_urls()
        for i in xrange(0, len(url_dics), chunk_size):
            yield url_dics[i:i+chunk_size]


    """
    def async_resolve_images_by_host_match(self, match_term, num_simul_urls):

        url_dics = self.get_url_chunks(num_simul_urls)
        print url_dics
        for url_dic_chunk in url_dics:

            splash_url_chunk = []
            for url_dic in url_dic_chunk:
                if "screenshot_path" not in url_dic:
                    if match_term in url_dic["host"]:
                        splash_url = SPLASH_URL + '/render.json?url=' + url_dic["url"] + '&html=1&png=1&wait=2.0&width=640&height=480&timeout=60&images=0'
                        splash_url_chunk.append((splash_url, url_dic["url"])

            rs = (grequests.get(u) for u in splash_url_chunk[0])
            responses = grequests.map(rs)
            for response in responses:
                url = response.url
                print response.url
                screenshot_path, html_rendered = self.process_splash_response(url, response)
                self.mmu.set_screenshot_path(url, screenshot_path)
                self.mmu.set_html_rendered(url, html_rendered)
                
    """

if __name__ == "__main__":
    
    sg = SplashGet(screenshot_dir = "/home/memex-punk/memex-dev/workspace/memex-pinterest/ui/static/images/screenshots")
    #sg.request_and_save("http://duskgytldkxiuqc6.onion/fedpapers/federa23.htm")
    #sg.resolve_images_by_host_match(".onion")
    sg.async_resolve_images_by_host_match(".", 10)
    
    
    