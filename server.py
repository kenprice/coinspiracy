# -*- coding: utf-8 -*-
from collections import OrderedDict, namedtuple
from typing import List, Union

import requests
import parsel
import json

import tornado.ioloop
import tornado.web
from tornado import gen

exchanges = ['bitfinex', 'bithumb', 'bittrex', 'binance', 'gdax', 'poloniex', 'kraken', 'etherdelta']
exchange_data = {'data': {}}

Price = namedtuple('Price', ['exchange', 'diff', 'diff_perc'])

def download_currency_data(currency):
    """
    Download currency data
    :param currency: currency name
    :return: dict of currency: usd_price
    """
    url = 'https://coinmarketcap.com/currency/' + currency + '/'
    resp = requests.get(url)
    sel = parsel.Selector(text=resp.text, base_url=resp.url)
    results = {}
    for row in sel.css('.table-condensed>tr')[1:]:
        name = row.css('.market-name::text').extract_first()
        usd = float(row.css('.price::attr(data-usd)').extract_first())
        if name and usd:
            results[name] = usd
    return results


def download_exchange(exchange):
    """
    Download exchange data
    :param exchange: exchange name
    :return: dict of currency: usd_price
    """
    url = 'https://coinmarketcap.com/exchanges/' + exchange + '/'
    resp = requests.get(url)
    sel = parsel.Selector(text=resp.text, base_url=resp.url)
    results = {}
    for row in sel.css('.table-condensed>tr')[1:]:
        name = row.css('.market-name::text').extract_first()
        usd = float(row.css('.price::attr(data-usd)').extract_first())
        if name and usd:
            results[name] = usd
    return results

def price_diff(data1, data2, sort_by='diff_perc', sort_reverse=True):
    """
    :param data1: exchange data1
    :param data2: exchange data2
    :param sort_by: sort results by key: exchange, diff, diff_perc
    :param sort_reverse: whether sort in descending order
    :return: sorted list of Price objects
    """
    results = []
    for k in data1:
        if k not in data2:
            continue
        diff = abs(data1[k] - data2[k])
        diff_perc = 100 - (data2[k] / data1[k] * 100)
        results.append(Price(k, diff, diff_perc))
    results = sorted(results, key=lambda price: getattr(price, sort_by), reverse=sort_reverse)
    return results

@gen.coroutine
def get_exchange_diffs():
    data_source = dict(map(lambda x: (x, download_exchange(x)), exchanges))
    results = {}

    for k1, data1 in data_source.items():
        for k2, data2 in data_source.items():
            if k1 == k2:
                continue

            price_d = price_diff(data1, data2)

            for k, diff, diff_perc in price_d:
                if k not in results:
                    results[k] = []

                result = {
                    "coin": k,
                    "exchange1": k1,
                    "exchange2": k2,
                    "exchange1_price": data1[k],
                    "exchange2_price": data2[k],
                    "diff": diff,
                    "diff_perc": diff_perc,
                }

                results[k].append(result)
    print("Updated")
    exchange_data['data'] = dict(results)

class MainHandler(tornado.web.RequestHandler):
    def initialize(self, exchange_data):
        self.exchange_data = exchange_data

    def get(self):
        self.write(json.dumps(self.exchange_data['data']))

class Application(tornado.web.Application):
    def __init__(self):
        handlers = [
            (r'/()$', tornado.web.StaticFileHandler, {'path': 'static/index.html'}),
            (r'/static/(.*)', tornado.web.StaticFileHandler, {'path': 'static/'}),
            (r'/exchange_data', MainHandler, {'exchange_data': exchange_data})]
        settings = dict(debug=False)
        tornado.web.Application.__init__(self, handlers, **settings)

if __name__ == "__main__":
    application = Application()
    http_server = tornado.httpserver.HTTPServer(application)
    http_server.listen(8888)

    get_exchange_diffs()
    tornado.ioloop.PeriodicCallback(get_exchange_diffs, 60000).start()
    tornado.ioloop.IOLoop.current().start()
