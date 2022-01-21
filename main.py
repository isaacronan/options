from models import OptionType
from utils import ScenarioTester

scenario_tester = ScenarioTester('SPY', 3)
scenario_details = scenario_tester.test(5, OptionType.Put, -0.03, -0.05)
print(scenario_details)