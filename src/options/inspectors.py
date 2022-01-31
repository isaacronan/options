from functools import lru_cache
from typing import Tuple

from datetime import date

from options.data.historical import get_historical_prices_by_symbol
from options.data.market import get_last, get_option_pairs
from options.models import Option, OptionBatch, OptionType, Period, TimeRange, HistoricalPrice
from options.utils.common import get_changed_price, get_weighted_price
from options.utils.historical import get_collapsed_historical_prices, get_weighted_historical_prices_by_group
from options.utils.options import get_option_batch_cost, get_return, MULTIPLIER, COMMISSION_PER_CONTRACT, \
    get_nearest_otm_call, get_nearest_otm_put, get_nearest_option, get_nearest_delta_call, get_nearest_delta_put


class OptionTradeScenario:
    def __init__(self, target_underlying_price: float, option: Option, contract_count: int):
        self.target_underlying_price = target_underlying_price
        self.option = option
        self.contract_count = contract_count

    @property
    def option_batch(self) -> OptionBatch:
        return OptionBatch(self.contract_count, self.option)

    @property
    def total_cost(self) -> float:
        return get_option_batch_cost(self.option_batch)

    @property
    def total_revenue(self) -> float:
        return get_return(self.option_batch, self.target_underlying_price)

    @property
    def total_profit(self) -> float:
        return self.total_revenue - self.total_cost


class OptionWriteScenario:
    def __init__(self, underlying_price: float, initial_num_shares: int, option: Option, num_periods: int):
        self.underlying_price = underlying_price
        self.initial_num_shares = initial_num_shares
        self.option = option
        self.num_periods = num_periods

    @property
    def periods(self) -> Tuple[Period, ...]:
        option_cost = self.option.last_price
        num_shares = self.initial_num_shares
        cash = 0
        periods = []
        for i in range(self.num_periods):
            num_contracts = int(num_shares / MULTIPLIER)
            premium = num_contracts * MULTIPLIER * option_cost
            cash += premium - (num_contracts * COMMISSION_PER_CONTRACT)
            if cash >= self.underlying_price * MULTIPLIER:
                purchase_batch_size = int(cash / (self.underlying_price * MULTIPLIER))
                cash -= purchase_batch_size * self.underlying_price * MULTIPLIER
                num_shares += purchase_batch_size * MULTIPLIER
            periods.append(Period(cash, num_shares))
        return tuple(periods)

    @property
    def shares_present_value(self) -> float:
        return self.underlying_price * self.initial_num_shares

    @property
    def shares_future_count(self) -> int:
        return self.periods[-1].num_shares

    @property
    def shares_future_value(self) -> float:
        return self.underlying_price * self.shares_future_count


class OptionInspector:
    def __init__(self, symbol: str, expiry_date: date):
        self.symbol = symbol
        self.expiry_date = expiry_date
        self.underlying_last_price, = get_last((self.symbol,))
        self.option_pairs = get_option_pairs(self.symbol, self.expiry_date)

    @property
    def calls(self) -> Tuple[Option, ...]:
        calls = tuple([option_pair.call for option_pair in self.option_pairs])
        return calls

    @property
    def puts(self) -> Tuple[Option, ...]:
        puts = tuple([option_pair.put for option_pair in self.option_pairs])
        return puts

    def get_nearest_otm_call(self, min_otm_percentage: float) -> Option:
        nearest = get_nearest_otm_call(self.calls, self.underlying_last_price, min_otm_percentage)
        return nearest

    def get_nearest_otm_put(self, min_otm_percentage: float) -> Option:
        nearest = get_nearest_otm_put(self.puts, self.underlying_last_price, min_otm_percentage)
        return nearest

    def get_nearest_delta_call(self, min_delta: float) -> Option:
        nearest = get_nearest_delta_call(self.calls, min_delta)
        return nearest

    def get_nearest_delta_put(self, min_delta: float) -> Option:
        nearest = get_nearest_delta_put(self.puts, min_delta)
        return nearest

    def test_option_write(
            self,
            initial_num_shares: int,
            option_type: OptionType,
            min_delta: float,
            num_periods: int
    ) -> OptionWriteScenario:
        nearest = self.get_nearest_delta_call(min_delta) if option_type == OptionType.Call else self.get_nearest_delta_put(min_delta)
        return OptionWriteScenario(
            self.underlying_last_price,
            initial_num_shares,
            nearest,
            num_periods,
        )

    def test_option_trade(
            self,
            contract_count: int,
            option_type: OptionType,
            target_strike_percentage_change: float,
            target_underlying_percentage_change: float
    ) -> OptionTradeScenario:
        target_underlying_price = get_changed_price(self.underlying_last_price, target_underlying_percentage_change)
        target_strike_price = get_changed_price(self.underlying_last_price, target_strike_percentage_change)
        options = tuple((option.call if option_type == OptionType.Call else option.put) for option in self.option_pairs)
        nearest_option = get_nearest_option(target_strike_price, options)

        return OptionTradeScenario(target_underlying_price, nearest_option, contract_count)


class PortfolioInspector:
    def __init__(self, symbols: Tuple[str, ...]):
        self.symbols = symbols

    def present_value(self, share_counts: Tuple[int, ...]) -> float:
        last_prices = get_last(tuple(symbol for symbol in self.symbols))
        return sum([get_weighted_price(last_price, share_count) for last_price, share_count in zip(last_prices, share_counts)])

    def portfolio_historical_prices(self, share_counts: Tuple[int, ...], time_range: TimeRange) -> Tuple[HistoricalPrice, ...]:
        historical_prices_by_symbol = self.historical_prices_by_symbol(time_range)
        weighted_historical_prices_by_symbol = get_weighted_historical_prices_by_group(historical_prices_by_symbol, share_counts)
        return get_collapsed_historical_prices(weighted_historical_prices_by_symbol)

    @lru_cache
    def historical_prices_by_symbol(self, time_range: TimeRange):
        return get_historical_prices_by_symbol(self.symbols, time_range)
