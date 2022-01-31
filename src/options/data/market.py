from typing import Tuple, Callable, Any

import requests
from rauth import OAuth1Service, OAuth1Session
import os
from datetime import date
from functools import lru_cache

from options.models import Option, OptionPair, OptionType, Stock, ExpiryType, Greeks


@lru_cache
def session() -> OAuth1Session:
    api_key = os.environ.get('ETRADE_KEY')
    api_secret = os.environ.get('ETRADE_SECRET')
    assert api_key and api_secret, 'Environment variables ETRADE_KEY and ETRADE_SECRET must be set.'

    service = OAuth1Service(
        name='etrade',
        consumer_key=api_key,
        consumer_secret=api_secret,
        request_token_url='https://api.etrade.com/oauth/request_token',
        access_token_url='https://api.etrade.com/oauth/access_token',
        authorize_url='https://us.etrade.com/e/t/etws/authorize?key={}&token={}',
        base_url='https://api.etrade.com/v1'
    )

    request_token, request_token_secret = service.get_request_token(params=dict(oauth_callback='oob', format='json'))
    authorize_url = service.authorize_url.format(service.consumer_key, request_token)
    print(authorize_url)
    code = input('code: ')
    _session = service.get_auth_session(
        request_token,
        request_token_secret,
        params=dict(oauth_verifier=code)
    )

    return _session


def get_last(symbols: Tuple[str, ...]) -> Tuple[float, ...]:
    _symbols = ','.join(symbols)
    quotes = session().get(f'https://api.etrade.com/v1/market/quote/{_symbols}.json').json()
    assert 'QuoteData' in quotes['QuoteResponse'], [message['description'] for message in quotes['QuoteResponse']['Messages']['Message']]
    quotes = [[q for q in quotes['QuoteResponse']['QuoteData'] if q['Product']['symbol'] == symbol][0] for symbol in symbols]
    last = [quote['All']['lastTrade'] for quote in quotes]
    return tuple(last)


def get_expiry_dates(symbol: str, expiry_type: ExpiryType = ExpiryType.Weekly) -> Tuple[date, ...]:
    params = dict(
        symbol=symbol,
        expiryType=expiry_type.value
    )
    _res = session().get('https://api.etrade.com/v1/market/optionexpiredate.json', params=params)
    if not _res.content:
        return ()
    res = _res.json()
    assert 'Error' not in res, res['Error']['message']
    expiry_dates = res['OptionExpireDateResponse']['ExpirationDate']
    data = tuple([
        date(*map(lambda field: int(expiry_date[field]), ['year', 'month', 'day'])) for expiry_date in expiry_dates
    ])
    return data


def get_option_pairs(symbol: str, expiry_date: date) -> Tuple[OptionPair, ...]:
    params = dict(
        symbol=symbol,
        chainType='CALLPUT',
        expiryYear=f'{expiry_date.year}',
        expiryMonth=f'{expiry_date.month}',
        expiryDay=f'{expiry_date.day}'
    )
    res = session().get('https://api.etrade.com/v1/market/optionchains.json', params=params).json()
    assert 'Error' not in res, res['Error']['message']
    option_pairs = res['OptionChainResponse']['OptionPair']
    data = tuple([
        OptionPair(
            call=Option(
                OptionType.Call,
                expiry_date,
                option_pair['Call']['strikePrice'],
                option_pair['Call']['lastPrice'],
                Greeks(
                    option_pair['Call']['OptionGreeks']['rho'],
                    option_pair['Call']['OptionGreeks']['vega'],
                    option_pair['Call']['OptionGreeks']['theta'],
                    option_pair['Call']['OptionGreeks']['delta'],
                    option_pair['Call']['OptionGreeks']['gamma'],
                    option_pair['Call']['OptionGreeks']['iv'],
                )
            ),
            put=Option(
                OptionType.Put,
                expiry_date,
                option_pair['Put']['strikePrice'],
                option_pair['Put']['lastPrice'],
                Greeks(
                    option_pair['Put']['OptionGreeks']['rho'],
                    option_pair['Put']['OptionGreeks']['vega'],
                    option_pair['Put']['OptionGreeks']['theta'],
                    option_pair['Put']['OptionGreeks']['delta'],
                    option_pair['Put']['OptionGreeks']['gamma'],
                    option_pair['Put']['OptionGreeks']['iv'],
                )
            )
        ) for option_pair in option_pairs
    ])
    return data


class Screener(tuple):
    def __new__(cls, stocks: Tuple[Stock, ...] = None) -> 'Screener':
        if stocks is None:
            rows = requests.get(
                'https://api.nasdaq.com/api/screener/stocks?tableonly=true&limit=25&offset=0&download=true',
                headers={'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36'}
            ).json()['data']['rows']
            return tuple.__new__(Screener, tuple([
                Stock(
                    symbol=row['symbol'],
                    name=row['name'],
                    last_price=float(row['lastsale'][1:]),
                    volume=int(row['volume']),
                )
                for row in rows
            ]))
        else:
            return tuple.__new__(Screener, stocks)

    def where(self, condition: Callable[[Stock], bool]) -> 'Screener':
        return Screener(tuple(filter(condition, self)))

    def asc(self, key: Callable[[Stock], Any]) -> 'Screener':
        return Screener(tuple(sorted(self, key=key)))

    def desc(self, key: Callable[[Stock], Any]) -> 'Screener':
        return Screener(tuple(sorted(self, key=key, reverse=True)))

    def head(self, count) -> 'Screener':
        return Screener(self[:count])

    def tail(self, count) -> 'Screener':
        return Screener(self[-count:])
