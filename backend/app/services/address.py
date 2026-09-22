
from dataclasses import dataclass

import httpx
from redis import Redis

from app.core.config import get_settings

@dataclass
class AddressResolved:
    cep: str
    address: str
    lat: float
    lng: float
    city: str
    state: str

class AddressLookupError(Exception):
    pass

def _get_redis() -> Redis | None:
    try:
        client = Redis.from_url(get_settings().redis_url, decode_responses=True)
        client.ping()
        return client
    except Exception:
        return None

def lookup_cep(cep: str) -> AddressResolved:
    digits = "".join(c for c in cep if c.isdigit())
    if len(digits) != 8:
        raise AddressLookupError("CEP inválido")

    cache_key = f"viacep:{digits}"
    redis = _get_redis()
    if redis:
        cached = redis.get(cache_key)
        if cached:
            parts = cached.split("|")
            if len(parts) == 5:
                return AddressResolved(
                    cep=digits,
                    address=parts[0],
                    lat=float(parts[1]),
                    lng=float(parts[2]),
                    city=parts[3],
                    state=parts[4],
                )

    with httpx.Client(timeout=15.0) as client:
        resp = client.get(f"https://viacep.com.br/ws/{digits}/json/")
        resp.raise_for_status()
        data = resp.json()
        if data.get("erro"):
            raise AddressLookupError(f"CEP {digits} não encontrado")

        logradouro = data.get("logradouro") or ""
        bairro = data.get("bairro") or ""
        city = data.get("localidade") or ""
        state = data.get("uf") or ""
        address_line = ", ".join(
            p for p in [logradouro, bairro, f"{city} - {state}", f"CEP {digits}"] if p
        )

        query = f"{logradouro}, {city}, {state}, Brasil".strip(", ")
        geo = client.get(
            "https://nominatim.openstreetmap.org/search",
            params={"q": query, "format": "json", "limit": 1},
            headers={"User-Agent": "RotaPay/1.0 (portfolio)"},
        )
        geo.raise_for_status()
        geo_data = geo.json()
        if not geo_data:
            geo2 = client.get(
                "https://nominatim.openstreetmap.org/search",
                params={
                    "city": city,
                    "state": state,
                    "country": "Brazil",
                    "format": "json",
                    "limit": 1,
                },
                headers={"User-Agent": "RotaPay/1.0 (portfolio)"},
            )
            geo2.raise_for_status()
            geo_data = geo2.json()
        if not geo_data:
            raise AddressLookupError("Não foi possível geocodificar o endereço")

        lat = float(geo_data[0]["lat"])
        lng = float(geo_data[0]["lon"])

    resolved = AddressResolved(
        cep=digits,
        address=address_line,
        lat=lat,
        lng=lng,
        city=city,
        state=state,
    )

    if redis:
        redis.setex(
            cache_key,
            86400,
            f"{resolved.address}|{resolved.lat}|{resolved.lng}|{resolved.city}|{resolved.state}",
        )

    return resolved
