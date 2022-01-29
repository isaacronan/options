from datetime import datetime, timedelta, date as _date


def to_timestamp(date: _date):
    return int(datetime(date.year, date.month, date.day).timestamp())


def days_ago(days: int) -> datetime:
    return datetime.now() - timedelta(days=days)
