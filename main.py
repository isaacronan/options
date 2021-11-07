from utils import get_scenario_details

scenario_details = get_scenario_details(
    symbol='SPY',
    days_until_expiry=3,
    contract_count=5,
    target_strike_decrease=0.03,
    target_underlying_decrease=0.05
)

print(scenario_details)