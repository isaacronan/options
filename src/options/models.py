from dataclasses import dataclass
from datetime import date, datetime
from enum import Enum
from typing import Optional


@dataclass(frozen=True)
class HistoricalPrice:
    date: date
    price: float


class OptionType(Enum):
    Call = 'Call'
    Put = 'Put'


@dataclass(frozen=True)
class Greeks:
    rho: float
    vega: float
    theta: float
    delta: float
    gamma: float
    iv: float


@dataclass(frozen=True)
class Option:
    option_type: OptionType
    expiry_date: date
    strike_price: float
    bid_price: float
    ask_price: float
    last_price: float
    volume: int
    open_interest: int
    greeks: Greeks


@dataclass(frozen=True)
class OptionPair:
    call: Option
    put: Option


@dataclass(frozen=True)
class OptionBatch:
    contract_count: int
    option: Option


@dataclass(frozen=True)
class Period:
    cash: float
    num_shares: int
    net_premium: float


@dataclass(frozen=True)
class DateRange:
    start: date
    end: date


@dataclass(frozen=True)
class TimeRange:
    start: datetime
    end: datetime


@dataclass(frozen=True)
class PriceChange:
    date_range: DateRange
    percentage: float


@dataclass(frozen=True)
class Stock:
    symbol: str
    name: str
    last_price: float
    volume: int


class ExpiryType(Enum):
    Weekly = 'WEEKLY'
    Monthly = 'MONTHLY'


@dataclass(frozen=True)
class QuoteDetail:
    last_price: float
    next_earnings_date: Optional[date]
    market_cap: float
    name: str
    high_52: float
    low_52: float
    average_volume: int
