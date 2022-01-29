from typing import Tuple, Callable

from toolz import groupby, concat

from options.models import HistoricalPrice, TimeRange, PriceChange, DateRange
from options.utils.common import get_weighted_price


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


def get_weighted_historical_prices(historical_prices: Tuple[HistoricalPrice, ...], weight: int) -> Tuple[HistoricalPrice, ...]:
    return tuple([
        HistoricalPrice(price.date, get_weighted_price(price.price, weight)) for price in historical_prices
    ])


def get_weighted_historical_prices_by_group(historical_prices_by_group: Tuple[Tuple[HistoricalPrice, ...], ...], weights: Tuple[int, ...]) -> Tuple[Tuple[HistoricalPrice, ...], ...]:
    return tuple([
        get_weighted_historical_prices(historical_prices, weight) for weight, historical_prices in zip(weights, historical_prices_by_group)
    ])


def get_collapsed_historical_prices(historical_prices_groups: Tuple[Tuple[HistoricalPrice, ...], ...]):
    assert len(set([len(historical_prices) for historical_prices in historical_prices_groups])) == 1, 'Different sized price ranges can not be collapsed.'
    historical_prices_by_date = groupby(lambda historical_price: historical_price.date, concat(historical_prices_groups))
    collapsed = [
        HistoricalPrice(_date, sum([historical_price.price for historical_price in historical_prices]))
        for _date, historical_prices in historical_prices_by_date.items()
    ]
    return tuple(collapsed)