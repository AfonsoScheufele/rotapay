
import pytest

from app.models.enums import FreightStatus
from app.services.status_machine import (
    IllegalTransitionError,
    assert_transition,
    can_transition,
)

def test_transicoes_legais() -> None:
    assert can_transition(FreightStatus.cotado, FreightStatus.aceito)
    assert can_transition(FreightStatus.aceito, FreightStatus.em_transito)
    assert can_transition(FreightStatus.em_transito, FreightStatus.entregue)
    assert can_transition(FreightStatus.entregue, FreightStatus.pago)
    assert can_transition(FreightStatus.cotado, FreightStatus.cancelado)

def test_transicao_ilegal_pula_status() -> None:
    assert not can_transition(FreightStatus.cotado, FreightStatus.entregue)
    with pytest.raises(IllegalTransitionError) as exc:
        assert_transition(FreightStatus.cotado, FreightStatus.pago)
    assert "ilegal" in str(exc.value).lower()

def test_pago_nao_cancela() -> None:
    assert not can_transition(FreightStatus.pago, FreightStatus.cancelado)
    with pytest.raises(IllegalTransitionError):
        assert_transition(FreightStatus.pago, FreightStatus.cancelado)

def test_cancelado_eh_terminal() -> None:
    assert not can_transition(FreightStatus.cancelado, FreightStatus.aceito)
