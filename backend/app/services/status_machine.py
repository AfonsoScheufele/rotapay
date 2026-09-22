
from app.models.enums import FreightStatus

ALLOWED_TRANSITIONS: dict[FreightStatus, set[FreightStatus]] = {
    FreightStatus.cotado: {FreightStatus.aceito, FreightStatus.cancelado},
    FreightStatus.aceito: {FreightStatus.em_transito, FreightStatus.cancelado},
    FreightStatus.em_transito: {FreightStatus.entregue, FreightStatus.cancelado},
    FreightStatus.entregue: {FreightStatus.pago},              
    FreightStatus.pago: set(),
    FreightStatus.cancelado: set(),
}

class IllegalTransitionError(Exception):
    def __init__(self, current: FreightStatus, target: FreightStatus) -> None:
        self.current = current
        self.target = target
        super().__init__(
            f"Transição ilegal: {current.value} → {target.value}"
        )

def can_transition(current: FreightStatus, target: FreightStatus) -> bool:
    return target in ALLOWED_TRANSITIONS.get(current, set())

def assert_transition(current: FreightStatus, target: FreightStatus) -> None:
    if not can_transition(current, target):
        raise IllegalTransitionError(current, target)
