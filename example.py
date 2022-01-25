from datetime import datetime, timedelta

from options.models import OptionType, TimeRange
from options.utils.current import Stock, days_elapsed, get_expiry_dates
from options.utils.historical import get_historical_prices, get_largest_negative_changes

symbol = 'SPY'

prices = get_historical_prices(symbol, TimeRange(datetime.now() - timedelta(days=10), datetime.now()))
print(prices)

changes = get_largest_negative_changes(prices, 3)
print(changes)

expiry_dates = get_expiry_dates(symbol)

stock = Stock(symbol, expiry_dates[0])
scenario = stock.test_option_trade(5, OptionType.Put, -0.03, -0.05)
print(scenario)