from datetime import date, datetime
from typing import NamedTuple


class HistoricalPrice(NamedTuple):
    date: date
    price: float


class Option(NamedTuple):
    expiry_date: date
    strike_price: float
    last_price: float


class OptionBatch(NamedTuple):
    contract_count: int
    option: Option


class ScenarioDetails(NamedTuple):
    expiry_date: date
    option: Option
    total_cost: float
    total_revenue: float
    total_profit: float


class DateRange(NamedTuple):
    start: date
    end: date


class TimeRange(NamedTuple):
    start: datetime
    end: datetime


class PriceChange(NamedTuple):
    date_range: DateRange
    percentage: float