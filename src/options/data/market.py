from typing import Tuple, Callable, Any, Union, Optional

import requests
import re
from rauth import OAuth1Service, OAuth1Session
import os
from datetime import date
from functools import lru_cache

from options.models import Option, OptionPair, OptionType, Stock, ExpiryType, Greeks, QuoteDetail


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


def get_quote_detail(symbols: Tuple[str, ...]) -> Tuple[QuoteDetail, ...]:
    _symbols = ','.join(symbols)
    params = dict(
        requireEarningsDate=True
    )
    quotes = session().get(f'https://api.etrade.com/v1/market/quote/{_symbols}.json', params=params).json()
    assert 'QuoteData' in quotes['QuoteResponse'], [message['description'] for message in quotes['QuoteResponse']['Messages']['Message']]
    quotes = [[q for q in quotes['QuoteResponse']['QuoteData'] if q['Product']['symbol'] == symbol][0] for symbol in symbols]

    def _date(d: str) -> Optional[date]:
        if not d:
            return None
        mm, dd, yyyy = d.split('/')
        return date(*map(int, [yyyy, mm, dd]))
    quote_details = [QuoteDetail(quote['All']['lastTrade'], _date(quote['All']['nextEarningDate'])) for quote in quotes]
    return tuple(quote_details)


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
            **dict([(key, Option(
                option_type,
                expiry_date,
                option_pair[res_key]['strikePrice'],
                option_pair[res_key]['bid'],
                option_pair[res_key]['ask'],
                option_pair[res_key]['lastPrice'],
                option_pair[res_key]['volume'],
                option_pair[res_key]['openInterest'],
                Greeks(
                    option_pair[res_key]['OptionGreeks']['rho'],
                    option_pair[res_key]['OptionGreeks']['vega'],
                    option_pair[res_key]['OptionGreeks']['theta'],
                    option_pair[res_key]['OptionGreeks']['delta'],
                    option_pair[res_key]['OptionGreeks']['gamma'],
                    option_pair[res_key]['OptionGreeks']['iv'],
                )
            )) for key, option_type, res_key in [('call', OptionType.Call, 'Call'), ('put', OptionType.Put, 'Put')]])
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
            pattern = re.compile(r'^\s*(\w+(/\w+)?)\s*$')
            return tuple.__new__(Screener, tuple([
                Stock(
                    symbol=pattern.search(row['symbol']).group(1).replace('/', '.'),
                    name=row['name'],
                    last_price=float(row['lastsale'][1:]),
                    volume=int(row['volume']),
                )
                for row in rows if pattern.search(row['symbol'])
            ]))
        else:
            return tuple.__new__(Screener, stocks)

    def __getitem__(self, item: Union[slice, int]) -> Union['Screener', Stock]:
        if isinstance(item, slice):
            return Screener(tuple(self)[item])
        else:
            return tuple(self)[item]

    def where(self, condition: Callable[[Stock], bool]) -> 'Screener':
        return Screener(tuple(filter(condition, self)))

    def asc(self, key: Callable[[Stock], Any]) -> 'Screener':
        return Screener(tuple(sorted(self, key=key)))

    def desc(self, key: Callable[[Stock], Any]) -> 'Screener':
        return Screener(tuple(sorted(self, key=key, reverse=True)))
