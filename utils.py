from typing import Tuple

from rauth import OAuth1Service
import os
import requests
from datetime import datetime, date, timedelta
from functools import reduce

from models import HistoricalPrice, Option, OptionBatch, ScenarioDetails

COMMISSION_PER_CONTRACT = 0.65
MULTIPLIER = 100


def get_historical_prices(symbol: str, start: datetime, end: datetime) -> Tuple[HistoricalPrice, ...]:
    _start = int(start.timestamp())
    _end = int(end.timestamp())
    url = f'https://query1.finance.yahoo.com/v7/finance/download/{symbol}?period1={_start}&period2={_end}&interval=1d&events=history&includeAdjustedClose=true'
    rows = requests.get(url, headers={'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/95.0.4638.54 Safari/537.36'}).text.split('\n')
    data = tuple([HistoricalPrice(date.fromisoformat(row[0]), float(row[4])) for row in map(lambda r: r.split(','), rows[1:])])
    return data


def get_session():
    api_key = os.environ.get('ETRADE_KEY')
    api_secret = os.environ.get('ETRADE_SECRET')

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
    session = service.get_auth_session(
        request_token,
        request_token_secret,
        params=dict(oauth_verifier=code)
    )

    return session


session = get_session()


def get_last(symbol: str) -> float:
    quotes = session.get(f'https://api.etrade.com/v1/market/quote/{symbol}.json').json()
    quote = [q for q in quotes['QuoteResponse']['QuoteData'] if q['Product']['symbol'] == symbol][0]
    last = quote['All']['lastTrade']
    return last


def get_options(symbol: str, expiry_date: date) -> Tuple[Option, ...]:
    params = dict(
        symbol=symbol,
        chainType='PUT',
        expiryYear=f'{expiry_date.year}',
        expiryMonth=f'{expiry_date.month}',
        expiryDay=f'{expiry_date.day}'
    )
    options = session.get('https://api.etrade.com/v1/market/optionchains.json', params=params).json()['OptionChainResponse']['OptionPair']
    data = tuple([Option(option['Put']['strikePrice'], option['Put']['lastPrice']) for option in options])
    return data


def get_nearest_option(target_strike_price: float, options: Tuple[Option, ...]) -> Option:
    return reduce(lambda cur, option: option if abs(option.strike_price - target_strike_price) < abs(cur.strike_price - target_strike_price) else cur, options, options[0])


def get_option_batch_cost(option_batch: OptionBatch) -> float:
    return option_batch.contract_count * (MULTIPLIER * option_batch.option.last_price + COMMISSION_PER_CONTRACT)


def get_decreased_price(price: float, percentage_decrease: float):
    return (1 - percentage_decrease) * price


def get_return(option_batch: OptionBatch, underlying_price: float):
    return option_batch.contract_count * MULTIPLIER * max([0, option_batch.option.strike_price - underlying_price])


def get_scenario_details(
        symbol: str,
        days_until_expiry: int,
        contract_count: int,
        target_strike_decrease: float,
        target_underlying_decrease: float
):
    last = get_last(symbol)
    expiry_date = date.today() + timedelta(days=days_until_expiry)
    options = get_options(symbol, expiry_date)
    target_underlying_price = get_decreased_price(last, target_underlying_decrease)
    target_strike_price = get_decreased_price(last, target_strike_decrease)
    nearest_option = get_nearest_option(target_strike_price, options)
    option_batch = OptionBatch(contract_count, nearest_option)
    total_cost = get_option_batch_cost(option_batch)
    total_revenue = get_return(option_batch, target_underlying_price)
    total_profit = total_revenue - total_cost

    return ScenarioDetails(expiry_date, nearest_option, total_cost, total_revenue, total_profit)
