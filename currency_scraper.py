    # -*- coding: utf-8 -*-
from collections import OrderedDict, namedtuple
from typing import List, Union

from datetime import datetime
import requests
import parsel
import json
import psycopg2

conn = psycopg2.connect('dbname=coinspiracy user=batman')
cur = conn.cursor()

exchanges = ['bitfinex', 'bithumb', 'bittrex', 'binance', 'gdax', 'poloniex', 'kraken', 'etherdelta']
exchange_data = {'data': {}}

currencies = ['bitcoin', 'ethereum', 'bitcoin-cash', 'ripple', 'litecoin', 'iota', 'dash', 'cardano', 'nem', 'bitcoin-gold', 'monero', 'eos', 'stellar', 'neo', 'ethereum-classic', 'qtum', 'populous', 'bitconnect', 'zcash', 
    'waves', 'omisego', 'tron', 'lisk', 'tether', 'stratis', 'ardor', 'hshare', 'bitshares', 'monacoin', 'nxt', 'bytecoin-bcn', 'steem', 'veritaseum', 'komodo', 'decred', 'salt', 'dogecoin', 'ark', 'binance-coin', 'einsteinium', 
    'augur', 'raiblocks', 'electroneum', 'siacoin', 'golem-network-tokens', 'vertcoin', 'pivx', 'aeternity', 'digixdao', 'factom', 'verge', 'gnosis-gno', 'maidsafecoin', 'tenx', 'status', 'qash', 'santiment', 'decentraland', 
    'basic-attention-token', 'power-ledger', 'syscoin', 'vechain', 'streamr-datacoin', 'kyber-network', 'nexus', 'bytom', 'byteball', 'bitcoindark', 'zcoin', 'walton', 'gas', 'digibyte', 'cryptonex', '0x', 'funfair', 'monaco', 
    'iconomi', 'raiden-network-token', 'request-network', 'gamecredits', 'gxshares', 'bancor', 'civic', 'nav-coin', 'aion', 'ubiq', 'pura', 'metaverse', 'revain', 'metal', 'blocknet', 'edgeless', 'rchain', 'storj', 'time-new-bank', 
    'chainlink', 'paypie', 'peercoin', 'ethos', 'ink', 'substratum', 'minexcoin']

Price = namedtuple('Price', ['exchange', 'diff', 'diff_perc'])

def download_currency_data(currencies):
    """
    Download currency data
    :param currency: currency name
    :return: dict of currency: usd_price
    """
    timestamp = datetime.utcnow()
    print (timestamp)

    for currency in currencies:
        url = 'https://coinmarketcap.com/currencies/' + currency
        resp = requests.get(url)
        sel = parsel.Selector(text=resp.text, base_url=resp.url)
        results = {}

        symbol = sel.css('.bold.hidden-xs *::text').get().replace('(','').replace(')','')

        for row in sel.css('#markets-table tr')[1:]:
            exchange = row.css('td')[1].css('a').xpath('@href').get().replace('/exchanges/','').replace('/','')
            currency_pair = row.css('td *::text')[2].get()
            usd_price = row.css('td')[4].css('span').xpath('@data-usd').get()
            btc_price = row.css('td')[4].css('span').xpath('@data-btc').get()

            if currency not in results:
                results[currency] = {}

            result = (
                symbol,                           # symbol
                exchange,                         # exchange_name
                timestamp,                        # timestamp
                currency_pair.split('/')[0],      # currency_pair1
                currency_pair.split('/')[1],      # currency_pair2
                usd_price,                        # usd_price
                btc_price                         # btc_price
            )

            print (symbol)

            try:
                cur.execute("""
                    INSERT INTO price (symbol, exchange_name, timestamp, currency_pair1, currency_pair2, price_usd, price_btc)
                    VALUES (%s, %s, TIMESTAMP %s, %s, %s, %s, %s)
                    ON CONFLICT (symbol, exchange_name, timestamp) DO NOTHING
                    """, result)
            except psycopg2.IntegrityError:
                conn.rollback()
            else:
                conn.commit()

    return results

download_currency_data(currencies)

cur.close()
conn.close()

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

