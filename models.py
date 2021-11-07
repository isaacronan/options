from datetime import date
from typing import NamedTuple


class HistoricalPrice(NamedTuple):
    date: date
    price: float


class Option(NamedTuple):
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