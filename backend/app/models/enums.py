
import enum

class UserRole(str, enum.Enum):
    admin = "admin"
    embarcador = "embarcador"
    motorista = "motorista"

class FreightStatus(str, enum.Enum):
    cotado = "cotado"
    aceito = "aceito"
    em_transito = "em_transito"
    entregue = "entregue"
    pago = "pago"
    cancelado = "cancelado"

class PaymentStatus(str, enum.Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"
    cancelled = "cancelled"


class WebhookEventStatus(str, enum.Enum):
    recebido = "recebido"
    processando = "processando"
    processado = "processado"
    falhou = "falhou"
