
from app.services.sla import estimate_sla_hours, haversine_km

def test_haversine_sp_curitiba_ordem_centenas_km() -> None:
    km = haversine_km(-23.561414, -46.655881, -25.428954, -49.267137)
    assert 300 < km < 450

def test_sla_curto_respeita_minimo() -> None:
    hours = estimate_sla_hours(10.0)
    assert hours == 72                         

def test_sla_longo_maior_que_curto_sem_estourar_max() -> None:
    curto = estimate_sla_hours(20.0)
    longo = estimate_sla_hours(3000.0)
    assert curto == 72
    assert longo > curto
    assert longo <= 336
    assert 90 <= longo <= 120
