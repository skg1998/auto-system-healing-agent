import pytest

from self_healing_agent.cli import _package_version, main


def test_version_flag_exits_zero():
    with pytest.raises(SystemExit) as excinfo:
        main(["--version"])
    assert excinfo.value.code == 0


def test_missing_command_returns_error_code():
    assert main([]) == 2


def test_package_version_is_non_empty():
    assert len(_package_version()) > 0
