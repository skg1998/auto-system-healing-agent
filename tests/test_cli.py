from self_healing_agent.cli import main


def test_cli_once_exits_zero():
    assert main(["once"]) == 0
