from datetime import datetime, timedelta

from options.models import OptionType, TimeRange
from options.utils.current import ScenarioTester
from options.utils.historical import get_historical_prices, get_largest_negative_changes

prices = get_historical_prices('SPY', TimeRange(datetime.now() - timedelta(days=10), datetime.now()))
print(prices)

changes = get_largest_negative_changes(prices, 3)
print(changes)

scenario_tester = ScenarioTester('SPY', 6)
scenario_details = scenario_tester.test(5, OptionType.Put, -0.03, -0.05)
print(scenario_details)