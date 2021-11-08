from utils import create_scenario_tester

scenario_details = create_scenario_tester(
    symbol='SPY',
    days_until_expiry=7
)(
    contract_count=5,
    target_strike_decrease=0.03,
    target_underlying_decrease=0.05
)

print(scenario_details)