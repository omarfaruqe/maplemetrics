import io
from unittest.mock import patch

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

TARGET = "apps.core.management.commands.refresh_data.call_command"


def run(*args, side_effect=None):
    out, err = io.StringIO(), io.StringIO()
    with patch(TARGET, side_effect=side_effect) as mocked:
        try:
            call_command("refresh_data", *args, stdout=out, stderr=err)
            error = None
        except CommandError as caught:
            error = caught
    return mocked, out.getvalue(), err.getvalue(), error


def names(mocked):
    return [call.args[0] for call in mocked.call_args_list]


def test_runs_ingests_then_forecasts_in_order():
    mocked, out, _, error = run()
    assert error is None
    assert names(mocked) == ["ingest_boc", "ingest_statcan", "run_forecasts"]
    assert "Refresh finished." in out


def test_skip_forecasts_leaves_them_alone():
    mocked, _, _, error = run("--skip-forecasts")
    assert error is None
    assert names(mocked) == ["ingest_boc", "ingest_statcan"]


def test_one_failing_source_does_not_stop_the_rest_but_fails_the_run():
    def fail_statcan(name, **kwargs):
        if name == "ingest_statcan":
            raise CommandError("Statistics Canada is down")

    mocked, _, err, error = run(side_effect=fail_statcan)
    assert names(mocked) == ["ingest_boc", "ingest_statcan", "run_forecasts"]
    assert "FAILED Statistics Canada: Statistics Canada is down" in err
    with pytest.raises(CommandError, match="Statistics Canada"):
        raise error
