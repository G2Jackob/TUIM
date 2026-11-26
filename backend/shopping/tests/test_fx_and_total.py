"""Zewnętrzne API kursów walut: sukces, cache, timeout, błędy, brak waluty + endpoint sumy."""

from decimal import Decimal

import pytest
import requests

from shopping import fx
from shopping.exceptions import ExternalServiceError, UnsupportedCurrency

pytestmark = pytest.mark.django_db


class FakeResponse:
    def __init__(self, status_code=200, payload=None, json_error=False):
        self.status_code = status_code
        self._payload = payload
        self._json_error = json_error

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"{self.status_code}")

    def json(self):
        if self._json_error:
            raise requests.exceptions.JSONDecodeError("bad", "", 0)
        return self._payload


def nbp(mid, date="2026-11-20"):
    return {"rates": [{"no": "1", "effectiveDate": date, "mid": mid}]}


@pytest.fixture
def api(monkeypatch):
    """Podmienia requests.get; `api.calls` zlicza zapytania, `api.responses` – kolejka odpowiedzi."""

    class Api:
        calls = []
        rates = {"eur": 4.25, "usd": 4.0}
        failure = None  # wyjątek lub FakeResponse zwracane zamiast kursu

    def fake_get(url, params=None, timeout=None):
        Api.calls.append((url, timeout))
        if isinstance(Api.failure, Exception):
            raise Api.failure
        if Api.failure is not None:
            return Api.failure
        code = url.rstrip("/").split("/")[-1]
        if code not in Api.rates:
            return FakeResponse(404)
        return FakeResponse(200, nbp(Api.rates[code]))

    Api.calls = []
    monkeypatch.setattr(fx.requests, "get", fake_get)
    return Api


# ---------------------------------------------------------------- klient fx


def test_same_currency_needs_no_api_call(api):
    rate = fx.get_rate("EUR", "EUR")
    assert rate.rate == 1 and not rate.stale
    assert api.calls == []


def test_pln_to_foreign(api):
    rate = fx.get_rate("PLN", "EUR")
    assert rate.rate == Decimal("0.235294")  # 1 / 4.25
    assert rate.date == "2026-11-20"
    assert rate.stale is False


def test_foreign_to_pln(api):
    assert fx.get_rate("EUR", "PLN").rate == Decimal("4.250000")


def test_cross_rate_between_foreign_currencies(api):
    assert fx.get_rate("EUR", "USD").rate == Decimal("1.062500")  # 4.25 / 4.0


def test_fresh_rate_is_cached(api):
    fx.get_rate("PLN", "EUR")
    fx.get_rate("PLN", "EUR")
    assert len(api.calls) == 1


def test_request_uses_configured_timeout(api):
    fx.get_rate("PLN", "EUR")
    assert api.calls[0][1] == 1


def test_unsupported_currency(api):
    with pytest.raises(UnsupportedCurrency):
        fx.get_rate("PLN", "XXX")


@pytest.mark.parametrize(
    "failure",
    [
        requests.Timeout("timeout"),
        requests.ConnectionError("refused"),
        FakeResponse(500),
        FakeResponse(200, json_error=True),
        FakeResponse(200, {"rates": []}),
        FakeResponse(200, {"bad": "shape"}),
        FakeResponse(200, nbp("abc")),
        FakeResponse(200, nbp(0)),
    ],
    ids=["timeout", "connection", "http500", "bad-json", "empty-rates", "bad-shape", "nan", "zero"],
)
def test_api_failure_without_cache_raises_external_service_error(api, failure):
    api.failure = failure
    with pytest.raises(ExternalServiceError):
        fx.get_rate("PLN", "EUR")


def test_api_failure_falls_back_to_stale_cache(api):
    from django.core.cache import cache

    fx.get_rate("PLN", "EUR")
    cache.delete("fx:nbp:EUR")  # świeży cache wygasł, „stary” został
    api.failure = requests.Timeout("timeout")
    rate = fx.get_rate("PLN", "EUR")
    assert rate.stale is True
    assert rate.rate == Decimal("0.235294")


# ---------------------------------------------------------------- endpoint /total/


def test_total_without_conversion(alice, make_list, make_item, api):
    lst = make_list(alice)
    make_item(lst, "mleko", quantity=Decimal("2"), estimated_price=Decimal("3.50"))
    make_item(lst, "ser", quantity=Decimal("0.5"), estimated_price=Decimal("20.00"))
    make_item(lst, "bez ceny")
    body = alice.client.get(f"/api/lists/{lst.id}/total/").json()
    assert body["total"] == "17.00"
    assert body["currency"] == "PLN"
    assert body["items_priced"] == 2 and body["items_without_price"] == 1
    assert body["converted"] is None
    assert api.calls == []  # bez parametru currency nie wołamy zewnętrznego API


def test_total_of_empty_list_is_zero(alice, make_list):
    lst = make_list(alice)
    assert alice.client.get(f"/api/lists/{lst.id}/total/").json()["total"] == "0.00"


def test_total_converted_to_other_currency(alice, make_list, make_item, api):
    lst = make_list(alice)
    make_item(lst, "x", quantity=Decimal("1"), estimated_price=Decimal("85.00"))
    body = alice.client.get(f"/api/lists/{lst.id}/total/?currency=eur").json()
    assert body["converted"]["currency"] == "EUR"
    assert body["converted"]["total"] == "20.00"  # 85 / 4.25
    assert body["converted"]["rate_date"] == "2026-11-20"
    assert body["converted"]["stale"] is False


def test_total_in_same_currency_as_list(alice, make_list, make_item, api):
    lst = make_list(alice, currency="EUR")
    make_item(lst, "x", estimated_price=Decimal("10"))
    body = alice.client.get(f"/api/lists/{lst.id}/total/?currency=EUR").json()
    assert body["converted"]["total"] == "10.00" and body["converted"]["rate"] == "1"
    assert api.calls == []


def test_total_when_external_api_is_down_returns_503_not_500(alice, make_list, make_item, api):
    lst = make_list(alice)
    make_item(lst, "x", estimated_price=Decimal("10"))
    api.failure = requests.Timeout("timeout")
    response = alice.client.get(f"/api/lists/{lst.id}/total/?currency=EUR")
    assert response.status_code == 503
    # reszta aplikacji działa
    assert alice.client.get(f"/api/lists/{lst.id}/total/").status_code == 200
    assert alice.client.get(f"/api/lists/{lst.id}/items/").status_code == 200


def test_total_uses_stale_rate_when_api_is_down(alice, make_list, make_item, api):
    from django.core.cache import cache

    lst = make_list(alice)
    make_item(lst, "x", estimated_price=Decimal("85"))
    alice.client.get(f"/api/lists/{lst.id}/total/?currency=EUR")
    cache.delete("fx:nbp:EUR")
    api.failure = requests.ConnectionError("down")
    body = alice.client.get(f"/api/lists/{lst.id}/total/?currency=EUR").json()
    assert body["converted"]["stale"] is True
    assert body["converted"]["total"] == "20.00"


def test_total_unsupported_currency_is_400(alice, make_list, api):
    lst = make_list(alice)
    assert alice.client.get(f"/api/lists/{lst.id}/total/?currency=XXX").status_code == 400


def test_total_malformed_currency_is_400(alice, make_list, api):
    lst = make_list(alice)
    response = alice.client.get(f"/api/lists/{lst.id}/total/?currency=euro")
    assert response.status_code == 400 and "currency" in response.json()


def test_total_requires_access(alice, carol, make_list):
    lst = make_list(alice)
    assert carol.client.get(f"/api/lists/{lst.id}/total/").status_code == 403


def test_member_can_read_total(alice, bob, make_list):
    lst = make_list(alice, members=[bob])
    assert bob.client.get(f"/api/lists/{lst.id}/total/").status_code == 200


# ---------------------------------------------------------------- endpoint /exchange-rates/


def test_exchange_rate_endpoint(alice, api):
    body = alice.client.get("/api/exchange-rates/?from=eur&to=pln").json()
    assert body == {"from": "EUR", "to": "PLN", "rate": "4.250000", "rate_date": "2026-11-20", "stale": False}


def test_exchange_rate_defaults_from_to_pln(alice, api):
    assert alice.client.get("/api/exchange-rates/?to=USD").json()["from"] == "PLN"


def test_exchange_rate_requires_to(alice, api):
    assert alice.client.get("/api/exchange-rates/").status_code == 400


def test_exchange_rate_rejects_bad_codes(alice, api):
    assert alice.client.get("/api/exchange-rates/?to=zł").status_code == 400
    assert alice.client.get("/api/exchange-rates/?from=1&to=EUR").status_code == 400


def test_exchange_rate_requires_auth(anon):
    assert anon.get("/api/exchange-rates/?to=EUR").status_code == 401
