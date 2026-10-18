import io
import json
import logging

from django.core.management import call_command
from django.urls import reverse

from apps.core.logs import JsonFormatter, RequestIdFilter, build_logging, request_id_var


def record(message="hello", **extra):
    made = logging.LogRecord("maplemetrics.test", logging.INFO, __file__, 1, message, (), None)
    made.__dict__.update(extra)
    return made


def test_json_formatter_writes_one_parsable_line_with_extras():
    request_id_var.set("abc123")
    made = record("loaded %s", rows=12)
    made.args = ("series",)
    RequestIdFilter().filter(made)
    line = JsonFormatter().format(made)
    assert "\n" not in line
    entry = json.loads(line)
    assert entry["message"] == "loaded series"
    assert entry["level"] == "INFO"
    assert entry["logger"] == "maplemetrics.test"
    assert entry["rows"] == 12
    assert entry["request_id"] == "abc123"
    assert entry["time"].endswith("+00:00")
    request_id_var.set("")


def test_json_formatter_includes_the_exception():
    try:
        raise ValueError("boom")
    except ValueError:
        import sys

        made = record("failed")
        made.exc_info = sys.exc_info()
    entry = json.loads(JsonFormatter().format(made))
    assert "ValueError: boom" in entry["exception"]


def test_build_logging_chooses_the_formatter():
    assert build_logging("json")["formatters"]["main"]["()"] == "apps.core.logs.JsonFormatter"
    assert "format" in build_logging("text")["formatters"]["main"]
    assert build_logging("text", "WARNING")["root"]["level"] == "WARNING"


def test_request_gets_an_id_header_and_a_log_line(client, db, caplog):
    with caplog.at_level(logging.INFO, logger="maplemetrics.request"):
        response = client.get(reverse("core:freshness"))
    request_id = response["X-Request-ID"]
    assert len(request_id) == 32
    lines = [r for r in caplog.records if r.name == "maplemetrics.request"]
    assert len(lines) == 1
    assert lines[0].status == 200
    assert lines[0].path == "/freshness/"
    assert lines[0].duration_ms >= 0


def test_a_safe_incoming_request_id_is_kept_and_an_unsafe_one_replaced(client, db):
    kept = client.get(reverse("core:freshness"), HTTP_X_REQUEST_ID="trace-42.a_b")
    assert kept["X-Request-ID"] == "trace-42.a_b"
    replaced = client.get(reverse("core:freshness"), HTTP_X_REQUEST_ID="bad id\r\nX: y")
    assert replaced["X-Request-ID"] != "bad id\r\nX: y"
    assert len(replaced["X-Request-ID"]) == 32


def test_each_log_line_during_a_request_carries_its_id(client, db, caplog):
    # The filter is attached to the handler, so use it directly the way the handler would.
    seen = []

    class Spy(logging.Handler):
        def emit(self, made):
            RequestIdFilter().filter(made)
            seen.append(made.request_id)

    spy = Spy()
    logging.getLogger("maplemetrics.request").addHandler(spy)
    logging.getLogger("maplemetrics.request").setLevel(logging.INFO)
    try:
        response = client.get(reverse("core:freshness"))
    finally:
        logging.getLogger("maplemetrics.request").removeHandler(spy)
    assert seen == [response["X-Request-ID"]]
    assert request_id_var.get() == ""


def test_healthchecks_are_logged_quietly_and_server_errors_loudly(client, db, caplog):
    with caplog.at_level(logging.DEBUG, logger="maplemetrics.request"):
        client.get(reverse("core:health"))
    assert [r.levelno for r in caplog.records if r.name == "maplemetrics.request"] == [
        logging.DEBUG
    ]
    caplog.clear()
    from unittest.mock import patch

    with (
        caplog.at_level(logging.INFO, logger="maplemetrics.request"),
        patch("apps.core.status.connection") as mocked,
    ):
        mocked.cursor.side_effect = RuntimeError("down")
        client.get(reverse("core:status"))
    levels = [r.levelno for r in caplog.records if r.name == "maplemetrics.request"]
    assert levels == [logging.ERROR]


def test_refresh_logs_each_step_and_the_failures(caplog):
    from unittest.mock import patch

    def fail_statcan(name, **kwargs):
        if name == "ingest_statcan":
            raise RuntimeError("down")

    target = "apps.core.management.commands.refresh_data.call_command"
    with (
        caplog.at_level(logging.INFO, logger="maplemetrics.refresh"),
        patch(target, side_effect=fail_statcan),
    ):
        try:
            call_command("refresh_data", stdout=io.StringIO(), stderr=io.StringIO())
        except Exception:  # noqa: BLE001
            pass
    messages = [r.getMessage() for r in caplog.records if r.name == "maplemetrics.refresh"]
    assert messages == [
        "refresh started",
        "refresh step finished",
        "refresh step failed",
        "refresh step finished",
        "refresh finished with failures",
    ]
