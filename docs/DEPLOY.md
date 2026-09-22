# Deploy Railway (API)

1. New project → Deploy from GitHub (`backend/` como root ou Dockerfile em `backend/Dockerfile`).
2. Add PostgreSQL e Redis (ou Upstash Redis URL).
3. Variables: copie de `.env.example` e ajuste para produção.
4. Cookie cross-origin com Vercel:
   - `COOKIE_SECURE=true`
   - `COOKIE_SAMESITE=none`
   - `FRONTEND_ORIGIN=https://<seu-app>.vercel.app`
5. Health check path: `/api/health`
6. Após o deploy, rode migrate: o `CMD` do Dockerfile já executa `alembic upgrade head`.

Webhook Mercado Pago (opcional):  
`https://<api>/api/webhooks/mercadopago`
