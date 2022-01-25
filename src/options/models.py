from datetime import date, datetime
from enum import Enum
from typing import NamedTuple, Tuple


class HistoricalPrice(NamedTuple):
    date: date
    price: float


class OptionType(Enum):
    Call = 'Call'
    Put = 'Put'


class Option(NamedTuple):
    option_type: OptionType
    expiry_date: date
    strike_price: float
    last_price: float


class OptionPair(NamedTuple):
    call: Option
    put: Option


class OptionBatch(NamedTuple):
    contract_count: int
    option: Option


class OptionTradeScenario(NamedTuple):
    underlying_price: float
    expiry_date: date
    option: Option
    total_cost: float
    total_revenue: float
    total_profit: float


class Period(NamedTuple):
    cash: float
    num_shares: int


class OptionWriteScenario(NamedTuple):
    underlying_price: float
    option: Option
    periods: Tuple[Period, ...]
    current_shares_value: float
    future_shares_value: float


class DateRange(NamedTuple):
    start: date
    end: date


class TimeRange(NamedTuple):
    start: datetime
    end: datetime


class PriceChange(NamedTuple):
    date_range: DateRange
    percentage: float


class ScreenerStock(NamedTuple):
    symbol: str
    name: str
    last_price: float
    volume: int


class ExpiryType(Enum):
    Weekly = 'WEEKLY'
    Monthly = 'MONTHLY'
