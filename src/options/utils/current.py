from typing import Tuple

from rauth import OAuth1Service
import os
from datetime import date, timedelta
from functools import reduce, lru_cache

from options.models import Option, OptionBatch, ScenarioDetails, OptionPair, OptionType

COMMISSION_PER_CONTRACT = 0.65
MULTIPLIER = 100


@lru_cache
def session():
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


def get_last(symbol: str) -> float:
    quotes = session().get(f'https://api.etrade.com/v1/market/quote/{symbol}.json').json()
    quote = [q for q in quotes['QuoteResponse']['QuoteData'] if q['Product']['symbol'] == symbol][0]
    last = quote['All']['lastTrade']
    return last


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
            call=Option(OptionType.Call, expiry_date, option_pair['Call']['strikePrice'], option_pair['Call']['lastPrice']),
            put=Option(OptionType.Put, expiry_date, option_pair['Put']['strikePrice'], option_pair['Put']['lastPrice'])
        ) for option_pair in option_pairs
    ])
    return data


def get_nearest_option(target_strike_price: float, options: Tuple[Option, ...]) -> Option:
    def _is_nearer(candidate: Option, current: Option):
        is_not_exceeding = candidate.strike_price <= target_strike_price if candidate.option_type == OptionType.Call else candidate.strike_price >= target_strike_price
        return is_not_exceeding and abs(candidate.strike_price - target_strike_price) < abs(current.strike_price - target_strike_price)

    return reduce(lambda cur, option: option if _is_nearer(option, cur) else cur, options, options[0])


def get_option_batch_cost(option_batch: OptionBatch) -> float:
    return option_batch.contract_count * (MULTIPLIER * option_batch.option.last_price + COMMISSION_PER_CONTRACT)


def get_changed_price(price: float, percentage_change: float):
    return (1 + percentage_change) * price


def get_return(option_batch: OptionBatch, underlying_price: float):
    delta = underlying_price - option_batch.option.strike_price if option_batch.option.option_type == OptionType.Call else option_batch.option.strike_price - underlying_price
    return option_batch.contract_count * MULTIPLIER * max([0, delta])


class ScenarioTester:
    def __init__(self, symbol: str, days_until_expiry: int):
        self.last = get_last(symbol)
        self.expiry_date = date.today() + timedelta(days=days_until_expiry)
        self.option_pairs = get_option_pairs(symbol, self.expiry_date)

    def test(
            self,
            contract_count: int,
            option_type: OptionType,
            target_strike_percentage_change: float,
            target_underlying_percentage_change: float
    ) -> ScenarioDetails:
        target_underlying_price = get_changed_price(self.last, target_underlying_percentage_change)
        target_strike_price = get_changed_price(self.last, target_strike_percentage_change)
        options = tuple((option.call if option_type == OptionType.Call else option.put) for option in self.option_pairs)
        nearest_option = get_nearest_option(target_strike_price, options)
        option_batch = OptionBatch(contract_count, nearest_option)
        total_cost = get_option_batch_cost(option_batch)
        total_revenue = get_return(option_batch, target_underlying_price)
        total_profit = total_revenue - total_cost

        return ScenarioDetails(target_underlying_price, self.expiry_date, nearest_option, total_cost, total_revenue, total_profit)
