import inspect
from datetime import datetime, timedelta, date as _date
from functools import reduce
from typing import Tuple, Any, Callable, Mapping

from options.models import DateRange, TimeRange


def to_timestamp(date: _date):
    return int(datetime(date.year, date.month, date.day).timestamp())


def days_ago(days: int) -> datetime:
    return datetime.now() - timedelta(days=days)


def days_elapsed(days: int) -> _date:
    return _date.today() + timedelta(days=days)


def last_days(days: int) -> TimeRange:
    return TimeRange(days_ago(days), datetime.now())


def is_overlap(date_range_a: DateRange, date_range_b: DateRange):
    return (date_range_b.start < date_range_a.end and date_range_a.start <= date_range_b.end) or (date_range_a.start < date_range_b.end and date_range_b.start <= date_range_a.end)


def get_weighted_price(price: float, weight: int) -> float:
    return weight * price


def get_changed_price(price: float, percentage_change: float):
    return (1 + percentage_change) * price


def create_balanced_portfolio(
        max_spend: float,
        items: Tuple[Any, ...],
        get_key: Callable[[Any], str],
        get_price: Callable[[Any], float],
        batch_size: int,
        cost_per_batch: float
) -> Mapping[str, int]:
    def _get_num_affordable_items(_remaining_spend):
        return len([i for i in items if _remaining_spend >= get_price(i) * batch_size + cost_per_batch])

    remaining_spend = max_spend
    items_desc_price = sorted(items, key=get_price, reverse=True)
    positions = {get_key(item): 0 for item in items}
    while _get_num_affordable_items(remaining_spend):
        for item in items_desc_price:
            if not _get_num_affordable_items(remaining_spend):
                break
            even_spend_per = remaining_spend / _get_num_affordable_items(remaining_spend)
            if even_spend_per >= get_price(item) * batch_size + cost_per_batch:
                quantity = int(even_spend_per / (get_price(item) * batch_size + cost_per_batch)) * batch_size
                positions[get_key(item)] += quantity
                remaining_spend -= get_price(item) * quantity + cost_per_batch * (quantity / batch_size)
            else:
                quantity = batch_size if remaining_spend >= batch_size * get_price(item) + cost_per_batch else 0
                positions[get_key(item)] += quantity
                remaining_spend -= get_price(item) * quantity + cost_per_batch * (quantity / batch_size)
    return positions


class Criteria:
    def __init__(self, param_name: str, *criteria: Callable[..., bool]):
        self.param_name = param_name
        self.criteria = tuple(criteria)

    def n(self, criterion) -> 'Criteria':
        return Criteria(self.param_name, *self.criteria, criterion)

    def __call__(self, **kwargs) -> Callable[[Any], bool]:
        def _partial(func):
            def _func(item):
                params = {**kwargs, self.param_name: item}
                param_names = list(inspect.signature(func).parameters.keys())
                return func(*[params[name] for name in param_names])
            return _func

        def _all(item):
            return reduce(lambda acc, func: acc and _partial(func)(item), self.criteria, True)

        return _all
