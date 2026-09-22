# RotaPay

Projeto que eu montei pra treinar um TMS simples no contexto BR: frete com papéis (admin, embarcador, motorista), mapa no OpenStreetMap e Pix só depois que a carga foi entregue.

A ideia é bem direta. Embarcador cria o frete, motorista aceita e atualiza o status, e o pagamento só entra quando chega em **entregue**. Eu não finjo TED pra CPF no sandbox: o sistema gera o Pix, confirma no webhook e grava o repasse líquido do motorista no banco.

## Stack

- Front: React, TypeScript, Vite, Leaflet
- API: Python, FastAPI, SQLAlchemy, Alembic
- Banco: PostgreSQL 16 + Redis 7
- Auth: JWT em cookie httpOnly (nada de localStorage)
- Pix: Mercado Pago sandbox, ou modo demo se não tiver token

Valores em centavos (`int`), tela em `R$ 1.234,56`, datas `DD/MM/AAAA`, fuso `America/Sao_Paulo`. Soft delete com `created_at`, `updated_at`, `deleted_at`.

Status:

`cotado → aceito → em_transito → entregue → pago` (e `cancelado` com regra)

No aceite do motorista eu calculo o SLA pela distância (Haversine), com média 45 km/h, buffer 1,5x, mínimo 72h e máximo 14 dias.

## Pix (o que eu fiz de propósito)

- Só gera Pix com frete **entregue**
- Webhook é idempotente (`event_key` único) e tem rate limit
- Guardo `driver_payout_recorded_cents` como repasse líquido
- Sem `MP_ACCESS_TOKEN`, roda em demo e tem botão pra simular o webhook no detalhe do frete

## Como eu testo o fluxo

1. Entro como `embarcador@rotapay.com` / `senha123` e crio um frete com CEP BR
2. Saio e entro como `motorista@rotapay.com` / `senha123`
3. Aceito → inicio trânsito → marco entregue
4. Volto no embarcador, gero o Pix e copio o código / QR
5. Simulo o webhook (demo) e vejo o frete ir pra **pago** e o dashboard atualizar

Tem seed também com `admin@rotapay.com`. Senha de todos: `senha123`. Nas listagens o documento vem mascarado.

## Subir local

```bash
cp .env.example .env
docker compose up -d
# Postgres na 5434, Redis na 6381

cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
python -m app.seed
uvicorn app.main:app --reload --port 8000

cd ../frontend
npm install && npm run dev
```

- App: http://localhost:5173
- Health: http://localhost:8000/api/health
- Docs da API: http://localhost:8000/docs

## Testes

```bash
cd backend && source .venv/bin/activate && pytest -q
```

Hoje cobrem transição ilegal de status, idempotência do webhook e o cálculo do SLA por distância.

## Prints

Deixei uns prints em [`docs/prints/`](docs/prints/) (login, lista, detalhe, dashboard e Pix).

Uso só pra estudo / demonstração.
