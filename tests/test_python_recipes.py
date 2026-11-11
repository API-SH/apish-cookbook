"""Dry runs of the Python recipes: every API call is answered from tests/fixtures, nothing goes online."""

import csv
import importlib.util
import json
import sys
import types
from pathlib import Path

import httpx
import pytest
from apish import Apish

ROOT = Path(__file__).resolve().parent.parent
FIXTURES = ROOT / "tests" / "fixtures"


def load(recipe, module):
    spec = importlib.util.spec_from_file_location(module, ROOT / "recipes" / recipe / f"{module}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class FakeApi:
    """Answers /<platform>/v1/<endpoint> with tests/fixtures/<platform>-<endpoint>.json and records each call."""

    def __init__(self, overrides=None):
        self.calls = []
        self.overrides = overrides or {}

    def __call__(self, request):
        route = request.url.path
        self.calls.append((route, dict(request.url.params)))
        assert request.headers["x-api-key"] == "test-key"
        if route in self.overrides:
            body = self.overrides[route](dict(request.url.params))
        else:
            name = route.strip("/").replace("/v1/", "-").replace("/", "-")
            body = json.loads((FIXTURES / f"{name}.json").read_text())
        return httpx.Response(200, json=body, headers={"x-credits-used": "1", "x-request-id": "test"})

    def client(self):
        return Apish("test-key", http_client=httpx.Client(transport=httpx.MockTransport(self)), max_retries=0)


def read_csv(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


ARGS = ["--keyword", "plumbers", "--areas", "Boulder, CO|Longmont, CO", "--min-rating", "0", "--min-reviews", "0"]


def test_lead_list(tmp_path, capsys):
    lead_list = load("google-maps-lead-list", "lead_list")
    api = FakeApi()
    out = tmp_path / "leads.csv"
    rows = lead_list.main([*ARGS, "--out", str(out)], apish=api.client())
    routes = [c[0] for c in api.calls]
    assert routes.count("/google-maps/v1/bulk-search") == 1
    assert routes.count("/google-maps/v1/contacts") == 1
    assert len(rows) == 5  # 6 results, one business in both areas
    written = read_csv(out)
    assert written[0]["email"] and not written[0]["email"].endswith("webagency.example")  # own domain first
    assert "?" not in "".join(r["website"] for r in written)
    assert "5 with a phone" in capsys.readouterr().out


def test_lead_list_retries_a_failed_area(tmp_path):
    lead_list = load("google-maps-lead-list", "lead_list")
    good = json.loads((FIXTURES / "google-maps-bulk-search.json").read_text())

    def bulk(params):
        if params.get("fresh") == "1":
            return {"results": [r for r in good["results"] if r["query"] in params["queries"].split("|")]}
        failed = json.loads(json.dumps(good))
        failed["results"][0].update(places=[], count=0, error="failed")
        return failed

    api = FakeApi({"/google-maps/v1/bulk-search": bulk})
    rows = lead_list.main([*ARGS, "--out", str(tmp_path / "l.csv")], apish=api.client())
    bulk_calls = [p for r, p in api.calls if r == "/google-maps/v1/bulk-search"]
    assert len(bulk_calls) == 2 and bulk_calls[1]["queries"] == "plumbers in Boulder, CO"
    assert len(rows) == 5


def test_lead_list_best_email():
    lead_list = load("google-maps-lead-list", "lead_list")
    email, rest = lead_list.best_email(["Info@Roofer.com", "x@agency.com", "not-an-email"], "https://www.roofer.com/")
    assert email == "info@roofer.com" and rest == ["info@roofer.com", "x@agency.com"]


def test_zillow_comps(tmp_path, capsys):
    comps = load("zillow-comps", "comps")
    api = FakeApi()
    out = tmp_path / "comps.csv"
    rows = comps.main(["149 NW 80th St, Seattle, WA 98117", "--months", "1200", "--size-range", "1",
                       "--out", str(out)], apish=api.client())
    assert [c[0] for c in api.calls] == ["/zillow/v1/autocomplete", "/zillow/v1/property", "/zillow/v1/search"]
    search = api.calls[2][1]
    assert search["status"] == "sold" and search["location"] == "98117" and search["home_type"] == "house"
    assert len(rows) >= 3
    assert [r["miles_away"] for r in rows] == sorted(r["miles_away"] for r in rows)
    assert "estimated value" in capsys.readouterr().out


def test_zillow_comps_skips_autocomplete_for_a_link(tmp_path):
    comps = load("zillow-comps", "comps")
    api = FakeApi()
    comps.main(["https://www.zillow.com/homedetails/48748070_zpid/", "--months", "1200", "--size-range", "1",
                "--out", str(tmp_path / "c.csv")], apish=api.client())
    assert api.calls[0][0] == "/zillow/v1/property"


def test_rank_tracker_records_history_and_drops(tmp_path, capsys):
    rank = load("google-rank-tracker", "rank")
    history = tmp_path / "rankings.csv"
    history.write_text("checked_at,keyword,country,position,url,title\n"
                       "2026-11-01T00:00:00Z,python tutorial,us,1,https://docs.python.org/3/tutorial/,x\n")
    api = FakeApi()
    rows = rank.main(["python tutorial", "--domain", "python.org", "--history", str(history)], apish=api.client())
    assert rows[0]["position"] == 4  # docs.python.org counts as python.org
    assert api.calls[0][1]["limit"] == "10"
    assert len(read_csv(history)) == 2
    assert "DROP python tutorial: 1 -> 4" in capsys.readouterr().out


def test_job_snapshot(tmp_path, capsys):
    snapshot = load("job-market-snapshot", "snapshot")
    api = FakeApi()
    out = tmp_path / "jobs.csv"
    jobs = snapshot.main(["data engineer", "Austin, TX", "--out", str(out)], apish=api.client())
    assert len(jobs) == 10  # 6 Indeed + 5 LinkedIn, one of them on both
    assert {j["work_mode"] for j in jobs} >= {"on-site", "remote"}
    assert "1 on both" in capsys.readouterr().out
    assert snapshot.yearly(50, "HOURLY") == 104000 and snapshot.yearly(1, None) is None


def test_review_export(tmp_path, capsys):
    export = load("review-export", "export_reviews")
    api = FakeApi()
    out = tmp_path / "reviews.csv"
    rows = export.main(["notion.so", "--pages", "3", "--out", str(out)], apish=api.client())
    assert [c[0] for c in api.calls] == ["/trustpilot/v1/company", "/trustpilot/v1/reviews"]
    assert len(rows) == 10 and sum(r["replied"] for r in rows) == 1
    assert len(read_csv(out)) == 10
    assert "exported 10 reviews" in capsys.readouterr().out


def test_review_export_since_stops_paging(tmp_path):
    export = load("review-export", "export_reviews")
    api = FakeApi()
    rows = export.main(["notion.so", "--since", "2030-01-01", "--out", str(tmp_path / "r.csv")], apish=api.client())
    assert rows == [] and len(api.calls) == 1


def test_review_export_to_google_sheets(tmp_path, monkeypatch):
    export = load("review-export", "export_reviews")
    appended = []

    class Worksheet:
        def col_values(self, n):
            return ["id", "review06"]  # header + one review already in the sheet

        def append_rows(self, rows, value_input_option):
            appended.extend(rows)

    class Book:
        def worksheet(self, title):
            assert title == "notion.so"
            return Worksheet()

    fake = types.ModuleType("gspread")
    fake.WorksheetNotFound = KeyError
    fake.service_account = lambda filename: types.SimpleNamespace(open_by_url=lambda url: Book())
    monkeypatch.setitem(sys.modules, "gspread", fake)
    monkeypatch.setenv("GOOGLE_SERVICE_ACCOUNT_FILE", str(tmp_path / "sa.json"))
    export.main(["notion.so", "--pages", "1", "--out", str(tmp_path / "r.csv"),
                 "--sheet", "https://docs.google.com/spreadsheets/d/abc/edit"], apish=FakeApi().client())
    assert len(appended) == 4 and len(appended[0]) == len(export.FIELDS)


@pytest.mark.parametrize("recipe,module", [
    ("google-maps-lead-list", "lead_list"), ("zillow-comps", "comps"), ("google-rank-tracker", "rank"),
    ("job-market-snapshot", "snapshot"), ("review-export", "export_reviews"),
])
def test_help(recipe, module, capsys):
    with pytest.raises(SystemExit) as done:
        load(recipe, module).parse_args(["--help"])
    assert done.value.code == 0 and "usage" in capsys.readouterr().out
