from typing import Tuple, Optional, Callable

from options.models import Option, OptionBatch, OptionType

COMMISSION_PER_CONTRACT = 0.65
MULTIPLIER = 100


def get_option_batch_cost(option_batch: OptionBatch) -> float:
    return option_batch.contract_count * (MULTIPLIER * option_batch.option.last_price + COMMISSION_PER_CONTRACT)


def get_return(option_batch: OptionBatch, underlying_price: float) -> float:
    delta = (underlying_price - option_batch.option.strike_price) if option_batch.option.option_type == OptionType.Call else (option_batch.option.strike_price - underlying_price)
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
