from typing import Tuple, Optional, Callable

from functools import reduce

from options.models import Option, OptionBatch, OptionType

COMMISSION_PER_CONTRACT = 0.65
MULTIPLIER = 100


def get_nearest_option(target_strike_price: float, options: Tuple[Option, ...]) -> Option:
    def _is_nearer(candidate: Option, current: Option):
        is_not_exceeding = candidate.strike_price <= target_strike_price if candidate.option_type == OptionType.Call else candidate.strike_price >= target_strike_price
        return is_not_exceeding and abs(candidate.strike_price - target_strike_price) < abs(current.strike_price - target_strike_price)

    return reduce(lambda cur, option: option if _is_nearer(option, cur) else cur, options, options[0])


def get_option_batch_cost(option_batch: OptionBatch) -> float:
    return option_batch.contract_count * (MULTIPLIER * option_batch.option.last_price + COMMISSION_PER_CONTRACT)


def get_return(option_batch: OptionBatch, underlying_price: float) -> float:
    delta = underlying_price - option_batch.option.strike_price if option_batch.option.option_type == OptionType.Call else option_batch.option.strike_price - underlying_price
    return option_batch.contract_count * MULTIPLIER * max([0, delta])


def get_highest_option(options: Tuple[Option, ...], option_criteria: Callable[[Option], bool] = lambda _: True) -> Optional[Option]:
    candidate_options = tuple(filter(option_criteria, options))
    if not candidate_options:
        return None
    return max(candidate_options, key=lambda option: option.last_price)


def get_lowest_option(options: Tuple[Option, ...], option_criteria: Callable[[Option], bool] = lambda _: True) -> Optional[Option]:
    candidate_options = tuple(filter(option_criteria, options))
    if not candidate_options:
        return None
    return min(candidate_options, key=lambda option: option.last_price)
