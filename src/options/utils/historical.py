from typing import Tuple, Callable

import requests
from datetime import date

from toolz import groupby

from options.models import HistoricalPrice, TimeRange, PriceChange, DateRange


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