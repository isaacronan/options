from datetime import datetime, timedelta, date as _date

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
