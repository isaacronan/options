from datetime import date, datetime
from enum import Enum
from typing import NamedTuple, Optional


class HistoricalPrice(NamedTuple):
    date: date
    price: float


class OptionType(Enum):
    Call = 'Call'
    Put = 'Put'


class Greeks(NamedTuple):
    rho: float
    vega: float
    theta: float
    delta: float
    gamma: float
    iv: float


class Option(NamedTuple):
    option_type: OptionType
    expiry_date: date
    strike_price: float
    bid_price: float
    ask_price: float
    last_price: float
    volume: int
    open_interest: int
    greeks: Greeks


class OptionPair(NamedTuple):
    call: Option
    put: Option


class OptionBatch(NamedTuple):
    contract_count: int
    option: Option


class Period(NamedTuple):
    cash: float
    num_shares: int
    net_premium: float


class DateRange(NamedTuple):
    start: date
    end: date


class TimeRange(NamedTuple):
    start: datetime
    end: datetime


class PriceChange(NamedTuple):
    date_range: DateRange
    percentage: float


class Stock(NamedTuple):
    symbol: str
    name: str
    last_price: float
    volume: int


class ExpiryType(Enum):
    Weekly = 'WEEKLY'
    Monthly = 'MONTHLY'


class QuoteDetail(NamedTuple):
    last_price: float
    next_earnings_date: Optional[date]
    market_cap: float  # marketCap
    company_name: str  # companyName
    high_52: float  # high52
    low_52: float  # low52
    average_volume: int  # averageVolume
