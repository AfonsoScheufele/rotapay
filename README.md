# RotaPay

TMS lite para o mercado brasileiro: frete com papéis (admin / embarcador / motorista), mapa OpenStreetMap e cobrança **Pix** (sandbox Mercado Pago ou demo local) ao concluir a entrega.

**Deploy:** _(cole a URL do front após publicar)_  
**Vídeo (2 a 3 min):** _(cole o link do Loom/YouTube)_  
**API / Swagger:** _(cole a URL)/docs_

## Problema de negócio

Embarcadores precisam acompanhar fretes de ponta a ponta e só liberar pagamento quando a carga foi entregue. Motoristas precisam ver fretes disponíveis, aceitar e atualizar status. A plataforma registra a cobrança Pix do embarcador e o **repasse líquido** ao motorista no banco, sem fingir TED/payout CPF no sandbox.

## Stack

| Camada | Tecnologia |
|--------|------------|
| Front | React, TypeScript, Vite, Leaflet |
| API | Python, FastAPI, SQLAlchemy, Alembic |
| Dados | PostgreSQL 16, Redis 7 |
| Auth | JWT em cookie **httpOnly** (nunca localStorage) |
| Pagamentos | Mercado Pago Pix (sandbox) ou modo demo |

Valores em **centavos (int)**; UI em `R$ 1.234,56`; datas `DD/MM/AAAA`; fuso `America/Sao_Paulo`. Soft delete com `created_at`, `updated_at`, `deleted_at`.

Fluxo de status (backend):

`cotado → aceito → em_transito → entregue → pago` (+ `cancelado` com regras)

**SLA:** no aceite do motorista, o prazo é estimado pela distância Haversine (origem/destino), com média 45 km/h, buffer 1,5x, mínimo 72h e máximo 14 dias.

## Honestidade no Pix

1. Embarcador gera cobrança Pix só com frete **entregue**.
2. Webhook confirma (idempotente por `event_key` único + rate limit).
3. Sistema grava `driver_payout_recorded_cents` (repasse líquido).
4. Não há TED/payout automático para CPF no sandbox.

Sem `MP_ACCESS_TOKEN`, a API gera Pix **demo** e o botão "Simular webhook" no detalhe aprova o pagamento localmente.

## Como testar o fluxo (5 passos)

1. Login `embarcador@rotapay.com` / `senha123` e crie um frete (CEPs BR).
2. Logout; login `motorista@rotapay.com` / `senha123`.
3. Aceite o frete → Iniciar trânsito → Marcar entregue (SLA nasce no aceite).
4. Volte como embarcador → **Gerar Pix** → QR / copia-e-cola.
5. Simular webhook (demo) ou pagamento sandbox → status **pago** → Dashboard atualiza.

Usuários seed: `admin@rotapay.com`, `embarcador@rotapay.com`, `motorista@rotapay.com` (senha `senha123`). Documentos mascarados nas listagens.

## Como rodar (local)

```bash
cp .env.example .env
docker compose up -d
# Postgres :5434 · Redis :6381

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
- OpenAPI: http://localhost:8000/docs  

## Testes

```bash
cd backend && source .venv/bin/activate && pytest -q
```

Cobre transição ilegal de status, idempotência do webhook e SLA por distância.

## Deploy (Vercel + Railway)

### Front (Vercel)

1. Root Directory: `frontend`
2. Build: `npm run build` · Output: `dist`
3. Env: `VITE_API_URL=https://SUA-API.up.railway.app`

Ver [`frontend/vercel.json`](frontend/vercel.json).

### API (Railway)

1. Deploy a partir de `backend/` com o [`Dockerfile`](backend/Dockerfile)
2. Adicione Postgres e Redis (ou Upstash)
3. Variáveis mínimas:

```
DATABASE_URL=...
REDIS_URL=...
JWT_SECRET=...
FRONTEND_ORIGIN=https://seu-app.vercel.app
COOKIE_SECURE=true
COOKIE_SAMESITE=none
API_PUBLIC_URL=https://SUA-API.up.railway.app
ENVIRONMENT=production
```

4. (Opcional) `MP_ACCESS_TOKEN` + webhook `https://SUA-API/api/webhooks/mercadopago`

Checklist pós-deploy: login seed, criar frete, fluxo até pago, cookie cross-site ok.

## Prints

Ver [`docs/prints/`](docs/prints/): login, fretes, detalhe (km + SLA), dashboard, Pix.

## Licença

Projeto de portfólio. Uso demonstrativo.
