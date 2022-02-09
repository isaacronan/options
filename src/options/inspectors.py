from functools import lru_cache
from typing import Tuple, Callable, Optional

from datetime import date

from options.data.historical import get_historical_prices_by_symbol
from options.data.market import get_last, get_option_pairs
from options.models import Option, OptionBatch, Period, TimeRange, HistoricalPrice
from options.utils.common import get_weighted_price
from options.utils.historical import get_collapsed_historical_prices, get_weighted_historical_prices_by_group
from options.utils.options import get_option_batch_cost, get_return, MULTIPLIER, COMMISSION_PER_CONTRACT, \
    get_highest_option, get_lowest_option, get_net_premium


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
    def __init__(self, share_price: float, initial_num_shares: int, write_option: Option, num_periods: int, hedge_option: Optional[Option] = None):
        self.share_price = share_price  # price per unit of accumulation (i.e. underlying price for calls, strike price for puts)
        self.initial_num_shares = initial_num_shares
        self.write_option = write_option
        self.num_periods = num_periods
        self.hedge_option = hedge_option

    @property
    def periods(self) -> Tuple[Period, ...]:
        num_shares = self.initial_num_shares
        cash = 0
        periods = []
        for i in range(self.num_periods):
            net_premium = get_net_premium(num_shares, self.write_option, self.hedge_option)
            cash += net_premium
            if cash >= self.share_price * MULTIPLIER + 0:
                purchase_batch_size = int(cash / (self.share_price * MULTIPLIER + 0))
                cash -= purchase_batch_size * (self.share_price * MULTIPLIER + 0)
                num_shares += purchase_batch_size * MULTIPLIER
            periods.append(Period(cash, num_shares, net_premium))
        return tuple(periods)

    @property
    def shares_present_value(self) -> float:
        return self.share_price * self.initial_num_shares

    @property
    def shares_future_count(self) -> int:
        return self.periods[-1].num_shares

    @property
    def shares_future_value(self) -> float:
        return self.share_price * self.shares_future_count


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

    def get_highest_call(self, option_criteria: Callable[[Option], bool] = lambda _: True) -> Optional[Option]:
        highest = get_highest_option(self.calls, option_criteria)
        return highest

    def get_highest_put(self, option_criteria: Callable[[Option], bool] = lambda _: True) -> Optional[Option]:
        highest = get_highest_option(self.puts, option_criteria)
        return highest

    def get_lowest_call(self, option_criteria: Callable[[Option], bool] = lambda _: True) -> Optional[Option]:
        lowest = get_lowest_option(self.calls, option_criteria)
        return lowest

    def get_lowest_put(self, option_criteria: Callable[[Option], bool] = lambda _: True) -> Optional[Option]:
        lowest = get_lowest_option(self.puts, option_criteria)
        return lowest


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
