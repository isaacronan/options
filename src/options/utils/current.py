from typing import Tuple, Callable, Any

import requests
from rauth import OAuth1Service, OAuth1Session
import os
from datetime import date, timedelta
from functools import reduce, lru_cache

from options.models import Option, OptionBatch, OptionPair, OptionType, ScreenerStock, ExpiryType, Period

COMMISSION_PER_CONTRACT = 0.65
MULTIPLIER = 100


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


def get_last(symbol: str) -> float:
    quotes = session().get(f'https://api.etrade.com/v1/market/quote/{symbol}.json').json()
    assert 'QuoteData' in quotes['QuoteResponse'], [message['description'] for message in quotes['QuoteResponse']['Messages']['Message']]
    quote = [q for q in quotes['QuoteResponse']['QuoteData'] if q['Product']['symbol'] == symbol][0]
    last = quote['All']['lastTrade']
    return last


def get_expiry_dates(symbol: str, expiry_type: ExpiryType = ExpiryType.Weekly) -> Tuple[date, ...]:
    params=dict(
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


def get_return(option_batch: OptionBatch, underlying_price: float) -> float:
    delta = underlying_price - option_batch.option.strike_price if option_batch.option.option_type == OptionType.Call else option_batch.option.strike_price - underlying_price
    return option_batch.contract_count * MULTIPLIER * max([0, delta])


def days_elapsed(days: int) -> date:
    return date.today() + timedelta(days=days)


def get_nearest_otm_call(calls: Tuple[Option, ...], last: float, min_otm_percentage: float) -> Option:
    otm_calls = sorted(calls, key=lambda o: o.strike_price, reverse=True)
    nearest = reduce(
        lambda acc, cur: cur if (cur.strike_price / last) >= (1 + min_otm_percentage) and cur.strike_price < acc.strike_price else acc,
        otm_calls,
        otm_calls[0]
    )
    return nearest


def get_nearest_otm_put(puts: Tuple[Option, ...], last: float, min_otm_percentage: float) -> Option:
    otm_puts = sorted(puts, key=lambda o: o.strike_price)
    nearest = reduce(
        lambda acc, cur: cur if (cur.strike_price / last) <= (1 - min_otm_percentage) and cur.strike_price > acc.strike_price else acc,
        otm_puts,
        otm_puts[0]
    )
    return nearest


class OptionTradeScenario:
    def __init__(self, target_underlying_price: float, option: Option, contract_count: int):
        self.target_underlying_price = target_underlying_price
        self.option = option
        self.contract_count = contract_count

    @property
    def option_batch(self) -> OptionBatch:
        return OptionBatch(self.contract_count, self.option)

    @property
    def total_cost(self) -> float:
        return get_option_batch_cost(self.option_batch)

    @property
    def total_revenue(self) -> float:
        return get_return(self.option_batch, self.target_underlying_price)

    @property
    def total_profit(self) -> float:
        return self.total_revenue - self.total_cost


class OptionWriteScenario:
    def __init__(self, underlying_price: float, initial_num_shares: int, option: Option, num_periods: int):
        self.underlying_price = underlying_price
        self.initial_num_shares = initial_num_shares
        self.option = option
        self.num_periods = num_periods

    @property
    def periods(self) -> Tuple[Period, ...]:
        option_cost = self.option.last_price
        num_shares = self.initial_num_shares
        cash = 0
        periods = []
        for i in range(self.num_periods):
            num_contracts = int(num_shares / MULTIPLIER)
            premium = num_contracts * MULTIPLIER * option_cost
            cash += premium - (num_contracts * COMMISSION_PER_CONTRACT)
            if cash >= self.underlying_price * MULTIPLIER:
                purchase_batch_size = int(cash / (self.underlying_price * MULTIPLIER))
                cash -= purchase_batch_size * self.underlying_price * MULTIPLIER
                num_shares += purchase_batch_size * MULTIPLIER
            periods.append(Period(cash, num_shares))
        return tuple(periods)

    @property
    def shares_present_value(self) -> float:
        return self.underlying_price * self.initial_num_shares

    @property
    def shares_future_count(self) -> int:
        return self.periods[-1].num_shares

    @property
    def shares_future_value(self) -> float:
        return self.underlying_price * self.shares_future_count


class Stock:
    def __init__(self, symbol: str, expiry_date: date):
        self.symbol = symbol
        self.expiry_date = expiry_date
        self.last_price = get_last(self.symbol)
        self.option_pairs = get_option_pairs(self.symbol, self.expiry_date)

    @property
    def calls(self) -> Tuple[Option, ...]:
        calls = tuple([option_pair.call for option_pair in self.option_pairs])
        return calls

    @property
    def puts(self) -> Tuple[Option, ...]:
        puts = tuple([option_pair.put for option_pair in self.option_pairs])
        return puts

    def get_nearest_otm_call(self, min_otm_percentage: float) -> Option:
        nearest = get_nearest_otm_call(self.calls, self.last_price, min_otm_percentage)
        return nearest

    def get_nearest_otm_put(self, min_otm_percentage: float) -> Option:
        nearest = get_nearest_otm_put(self.puts, self.last_price, min_otm_percentage)
        return nearest

    def test_option_write(
            self,
            initial_num_shares: int,
            option_type: OptionType,
            min_otm_percentage: float,
            num_periods: int
    ) -> OptionWriteScenario:
        nearest = self.get_nearest_otm_call(min_otm_percentage) if option_type == OptionType.Call else self.get_nearest_otm_put(min_otm_percentage)
        return OptionWriteScenario(
            self.last_price,
            initial_num_shares,
            nearest,
            num_periods,
        )

    def test_option_trade(
            self,
            contract_count: int,
            option_type: OptionType,
            target_strike_percentage_change: float,
            target_underlying_percentage_change: float
    ) -> OptionTradeScenario:
        target_underlying_price = get_changed_price(self.last_price, target_underlying_percentage_change)
        target_strike_price = get_changed_price(self.last_price, target_strike_percentage_change)
        options = tuple((option.call if option_type == OptionType.Call else option.put) for option in self.option_pairs)
        nearest_option = get_nearest_option(target_strike_price, options)

        return OptionTradeScenario(target_underlying_price, nearest_option, contract_count)


class Screener(tuple):
    def __new__(cls, stocks: Tuple[ScreenerStock, ...] = None) -> 'Screener':
        if stocks is None:
            rows = requests.get(
                'https://api.nasdaq.com/api/screener/stocks?tableonly=true&limit=25&offset=0&download=true',
                headers={'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36'}
            ).json()['data']['rows']
            return tuple.__new__(Screener, tuple([
                ScreenerStock(
                    symbol=row['symbol'],
                    name=row['name'],
                    last_price=float(row['lastsale'][1:]),
                    volume=int(row['volume']),
                )
                for row in rows
            ]))
        else:
            return tuple.__new__(Screener, stocks)

    def where(self, condition: Callable[[ScreenerStock], bool]) -> 'Screener':
        return Screener(tuple(filter(condition, self)))

    def asc(self, key: Callable[[ScreenerStock], Any]) -> 'Screener':
        return Screener(tuple(sorted(self, key=key)))

    def desc(self, key: Callable[[ScreenerStock], Any]) -> 'Screener':
        return Screener(tuple(sorted(self, key=key, reverse=True)))

    def head(self, count) -> 'Screener':
        return Screener(self[:count])

    def tail(self, count) -> 'Screener':
        return Screener(self[-count:])
