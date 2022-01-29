from typing import Tuple

import requests
from datetime import date

from options.models import HistoricalPrice, TimeRange


def get_historical_prices(symbol: str, time_range: TimeRange) -> Tuple[HistoricalPrice, ...]:
    start = int(time_range.start.timestamp())
    end = int(time_range.end.timestamp())
    url = f'https://query1.finance.yahoo.com/v7/finance/download/{symbol}?period1={start}&period2={end}&interval=1d&events=history&includeAdjustedClose=true'
    rows = requests.get(url, headers={'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/95.0.4638.54 Safari/537.36'}).text.split('\n')
    data = tuple([HistoricalPrice(date.fromisoformat(row[0]), float(row[4])) for row in map(lambda r: r.split(','), rows[1:])])
    return data


def get_historical_prices_by_symbol(symbols: Tuple[str, ...], time_range: TimeRange) -> Tuple[Tuple[HistoricalPrice, ...], ...]:
    historical_prices_by_symbol = [get_historical_prices(symbol, time_range) for symbol in symbols]
    return tuple(historical_prices_by_symbol)
