from typing import Tuple, Callable

from rauth import OAuth1Service
import os
import requests
from datetime import date, timedelta
from functools import reduce, lru_cache

from toolz import groupby

from models import HistoricalPrice, Option, OptionBatch, ScenarioDetails, TimeRange, PriceChange, DateRange, OptionPair, \
    OptionType

COMMISSION_PER_CONTRACT = 0.65
MULTIPLIER = 100


def get_historical_prices(symbol: str, time_range: TimeRange) -> Tuple[HistoricalPrice, ...]:
    start = int(time_range.start.timestamp())
    end = int(time_range.end.timestamp())
    url = f'https://query1.finance.yahoo.com/v7/finance/download/{symbol}?period1={start}&period2={end}&interval=1d&events=history&includeAdjustedClose=true'
    rows = requests.get(url, headers={'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/95.0.4638.54 Safari/537.36'}).text.split('\n')
    data = tuple([HistoricalPrice(date.fromisoformat(row[0]), float(row[4])) for row in map(lambda r: r.split(','), rows[1:])])
    return data


def get_price_changes(prices: Tuple[HistoricalPrice, ...], period_days: int) -> Tuple[PriceChange, ...]:
    return tuple([PriceChange(
        DateRange(a.date, b.date),
        (b.price / a.price) - 1
    ) for a, b in zip(prices[:-period_days], prices[period_days:])])


def get_largest_change(changes: Tuple[PriceChange, ...], is_larger: Callable[[float, float], bool]) -> PriceChange:
    largest_change = changes[0]
    for change in changes:
        if is_larger(change.percentage, largest_change.percentage):
            largest_change = change
    return largest_change


def get_largest_changes(prices: Tuple[HistoricalPrice, ...], max_period_days: int, is_larger: Callable[[float, float], bool]) -> Tuple[PriceChange, ...]:
    all_changes = ()
    for i in range(1, max_period_days + 1):
        all_changes = all_changes + get_price_changes(prices, period_days=i)
    changes_by_start_date = groupby(lambda change: change.date_range.start, all_changes)
    largest_changes = tuple([get_largest_change(tuple(changes), is_larger) for _, changes in changes_by_start_date.items()])
    return largest_changes


def get_largest_negative_changes(prices: Tuple[HistoricalPrice, ...], max_period_days: int) -> Tuple[PriceChange, ...]:
    return get_largest_changes(prices, max_period_days, lambda percentage, current: percentage < current)


def get_largest_positive_changes(prices: Tuple[HistoricalPrice, ...], max_period_days: int) -> Tuple[PriceChange, ...]:
    return get_largest_changes(prices, max_period_days, lambda percentage, current: percentage > current)


def is_overlap(date_range_a: DateRange, date_range_b: DateRange):
    return (date_range_b.start < date_range_a.end and date_range_a.start <= date_range_b.end) or (date_range_a.start < date_range_b.end and date_range_b.start <= date_range_a.end)


@lru_cache
def session():
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


def get_nearest_option(option_type: OptionType, target_strike_price: float, options: Tuple[Option, ...]) -> Option:
    def _is_nearer(candidate: Option, current: Option):
        is_not_exceeding = candidate.strike_price <= target_strike_price if option_type == OptionType.Call else candidate.strike_price >= target_strike_price
        return is_not_exceeding and abs(candidate.strike_price - target_strike_price) < abs(current.strike_price - target_strike_price)

    return reduce(lambda cur, option: option if _is_nearer(option, cur) else cur, options, options[0])


def get_option_batch_cost(option_batch: OptionBatch) -> float:
    return option_batch.contract_count * (MULTIPLIER * option_batch.option.last_price + COMMISSION_PER_CONTRACT)


def get_changed_price(price: float, percentage_change: float):
    return (1 + percentage_change) * price


def get_return(option_type: OptionType, option_batch: OptionBatch, underlying_price: float):
    delta = underlying_price - option_batch.option.strike_price if option_type == OptionType.Call else option_batch.option.strike_price - underlying_price
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
        nearest_option = get_nearest_option(option_type, target_strike_price, options)
        option_batch = OptionBatch(contract_count, nearest_option)
        total_cost = get_option_batch_cost(option_batch)
        total_revenue = get_return(option_type, option_batch, target_underlying_price)
        total_profit = total_revenue - total_cost

        return ScenarioDetails(target_underlying_price, self.expiry_date, nearest_option, total_cost, total_revenue, total_profit)
