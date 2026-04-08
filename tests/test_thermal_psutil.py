from unittest.mock import MagicMock, patch

from self_healing_agent.adapters.thermal_psutil import first_cpu_thermal_celsius


def test_first_cpu_thermal_returns_none_when_unsupported():
    with patch("self_healing_agent.adapters.thermal_psutil.psutil") as m:
        m.sensors_temperatures.side_effect = NotImplementedError()
        assert first_cpu_thermal_celsius() is None


def test_first_cpu_thermal_returns_first_positive():
    ent = MagicMock()
    ent.current = 55.0
    with patch("self_healing_agent.adapters.thermal_psutil.psutil") as m:
        m.sensors_temperatures.return_value = {"cpu": [(ent)]}
        assert first_cpu_thermal_celsius() == 55.0
