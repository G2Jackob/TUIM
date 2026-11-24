"""Klient zewnętrznego API kursów walut (NBP, tabela A – bez klucza API).

NBP podaje średni kurs waluty obcej w PLN. Kurs krzyżowy:
    from → to  =  kurs_PLN(from) / kurs_PLN(to)

Odporność na awarie (FR-08):
  * timeout ({EXCHANGE_API_TIMEOUT}s) i obsługa błędów sieci / HTTP / złego JSON-a,
  * świeży cache (EXCHANGE_RATE_CACHE_TTL), a przy awarii API – „stary” cache (7 dni)
    zwracany z flagą stale=True,
  * gdy nie ma nawet starego cache → ExternalServiceError (HTTP 503), reszta
    aplikacji działa normalnie.
"""

import logging
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

import requests
from django.conf import settings
from django.core.cache import cache

from .exceptions import ExternalServiceError, UnsupportedCurrency

logger = logging.getLogger(__name__)

STALE_TTL_SECONDS = 7 * 24 * 3600
RATE_QUANT = Decimal("0.000001")


@dataclass(frozen=True)
class Rate:
    rate: Decimal
    date: str | None
    stale: bool


def _fetch_pln_rate(code: str) -> dict:
    url = f"{settings.EXCHANGE_API_BASE_URL.rstrip('/')}/exchangerates/rates/a/{code.lower()}/"
    response = requests.get(url, params={"format": "json"}, timeout=settings.EXCHANGE_API_TIMEOUT)
    if response.status_code == 404:
        raise UnsupportedCurrency(f"Waluta {code} nie jest obsługiwana przez dostawcę kursów.")
    response.raise_for_status()
    entry = response.json()["rates"][-1]
    rate = Decimal(str(entry["mid"]))
    if rate <= 0:
        raise ValueError("kurs musi być dodatni")
    return {"rate": str(rate), "date": entry.get("effectiveDate")}


def _pln_rate(code: str) -> tuple[dict, bool]:
    """Zwraca ({"rate": str, "date": str|None}, stale)."""
    if code == "PLN":
        return {"rate": "1", "date": None}, False

    fresh_key = f"fx:nbp:{code}"
    stale_key = f"{fresh_key}:stale"

    cached = cache.get(fresh_key)
    if cached:
        return cached, False

    try:
        data = _fetch_pln_rate(code)
    except UnsupportedCurrency:
        raise
    except (requests.RequestException, ValueError, KeyError, IndexError, InvalidOperation) as exc:
        logger.warning("Błąd zewnętrznego API kursów walut (%s): %s", code, exc)
        stale = cache.get(stale_key)
        if stale:
            return stale, True
        raise ExternalServiceError() from exc

    cache.set(fresh_key, data, settings.EXCHANGE_RATE_CACHE_TTL)
    cache.set(stale_key, data, STALE_TTL_SECONDS)
    return data, False


def get_rate(from_code: str, to_code: str) -> Rate:
    if from_code == to_code:
        return Rate(Decimal("1"), None, False)

    from_data, from_stale = _pln_rate(from_code)
    to_data, to_stale = _pln_rate(to_code)

    rate = (Decimal(from_data["rate"]) / Decimal(to_data["rate"])).quantize(RATE_QUANT)
    dates = [d for d in (from_data["date"], to_data["date"]) if d]
    return Rate(rate, max(dates) if dates else None, from_stale or to_stale)
