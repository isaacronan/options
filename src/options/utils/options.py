from typing import Tuple

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


def get_nearest_otm_call(calls: Tuple[Option, ...], underlying_last_price: float, min_otm_percentage: float) -> Option:
    otm_calls = sorted(calls, key=lambda o: o.strike_price, reverse=True)
    nearest = reduce(
        lambda acc, cur: cur if (cur.strike_price / underlying_last_price) >= (1 + min_otm_percentage) and cur.strike_price < acc.strike_price else acc,
        otm_calls,
        otm_calls[0]
    )
    return nearest


def get_nearest_otm_put(puts: Tuple[Option, ...], underlying_last_price: float, min_otm_percentage: float) -> Option:
    otm_puts = sorted(puts, key=lambda o: o.strike_price)
    nearest = reduce(
        lambda acc, cur: cur if (cur.strike_price / underlying_last_price) <= (1 - min_otm_percentage) and cur.strike_price > acc.strike_price else acc,
        otm_puts,
        otm_puts[0]
    )
    return nearest


def get_nearest_delta_call(calls: Tuple[Option, ...], min_delta: float) -> Option:
    assert min_delta > 0, 'Delta must be > 0 for call options.'
    otm_calls = sorted(calls, key=lambda o: o.strike_price, reverse=True)
    nearest = reduce(
        lambda acc, cur: cur if min_delta > cur.greeks.delta > acc.greeks.delta else acc,
        otm_calls,
        otm_calls[0]
    )
    return nearest


def get_nearest_delta_put(puts: Tuple[Option, ...], min_delta: float) -> Option:
    assert min_delta < 0, 'Delta must be < 0 for call options.'
    otm_puts = sorted(puts, key=lambda o: o.strike_price)
    nearest = reduce(
        lambda acc, cur: cur if min_delta < cur.greeks.delta < acc.greeks.delta else acc,
        otm_puts,
        otm_puts[0]
    )
    return nearest
