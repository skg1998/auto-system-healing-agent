from self_healing_agent.adapters.fake import FakeMetricsAdapter

# PsutilAdapter is imported from self_healing_agent.adapters.psutil_adapter where needed
# so tests can run without psutil until the environment installs dependencies.

__all__ = ["FakeMetricsAdapter"]
