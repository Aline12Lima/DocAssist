# Deploy na Railway (plano gratuito)

O DocAssist roda em dois "sabores" a partir do mesmo código. A escolha é feita só por
variáveis de ambiente:

| | Local (`docker-compose.yml`) | Nuvem (`Dockerfile.nuvem`) |
| --- | --- | --- |
| Embeddings | e5-small, na CPU | Gemini (`gemini-embedding-001`), por API |
| Reranker | ligado (20 candidatos) | desligado |
| "Não encontrei" sem LLM | nota do reranker ≥ 2,0 | distância ≤ 0,32 |
| Banco | Postgres | SQLite no volume (`/data/docassist.db`) |
| Vetores | Chroma em `./chroma_data` | Chroma no volume (`/data/chroma`) |
| Cache e limite por minuto | Redis | Redis (sem volume) |
| Métricas | Prometheus em `:9090` | só o `/metrics` (sem Prometheus) |
| Memória da API | ~570 MB | ~135 MB |

Os números e o porquê de cada troca estão em `docs/experimentos.md` (E7, calibração do
limiar e imagem leve).

## Limites do plano gratuito que decidiram a arquitetura

Fonte: [Free plan](https://docs.railway.com/pricing/free-plan) e
[Volumes](https://docs.railway.com/volumes/reference).

- 1 projeto, até 3 serviços, cada um com até 1 vCPU e 0,5 GB de RAM → a API com PyTorch
  (~570 MB) não cabe; a imagem leve cabe.
- **1 volume por projeto**, de 0,5 GB → o volume fica com a API (Chroma + SQLite). O
  Postgres precisaria de um volume próprio, por isso a nuvem usa SQLite.
- US$ 1 de uso por mês, sem cartão. Acabou o crédito, os serviços param (sem cobrança).
- Os serviços "dormem" depois de 5 a 10 minutos sem tráfego de saída e acordam na próxima
  requisição. A primeira requisição depois de dormir pode demorar ou voltar 502.

## Serviços

```
              internet (HTTPS)
                     │
           ┌─────────▼──────────┐       rede privada        ┌──────────────────┐
           │  DocAssist (API)   │ ─────────────────────────▶ │ redis:7-alpine   │
           │  Dockerfile.nuvem  │  redis.railway.internal    │ sem volume,      │
           │  volume em /data   │                            │ sem domínio      │
           └─────────┬──────────┘                            └──────────────────┘
                     │ HTTPS
         Gemini (embeddings + LLM reserva) · Groq (LLM)
```

O Redis guarda só coisas temporárias (cache das respostas e contagem do limite por minuto).
Se ele reiniciar e perder tudo, nada se perde de verdade. Ele não tem domínio público: só a
API, dentro do projeto, consegue falar com ele.

## Variáveis da API na Railway

| Variável | Valor | Por quê |
| --- | --- | --- |
| `RAILWAY_DOCKERFILE_PATH` | `Dockerfile.nuvem` | sem ela, a Railway usa o `Dockerfile` da raiz (com PyTorch) |
| `REDIS_URL` | `redis://${{redis.RAILWAY_PRIVATE_DOMAIN}}:6379/0` | referência ao serviço `redis` pela rede privada |
| `GROQ_API_KEY` | (segredo) | LLM principal |
| `GEMINI_API_KEY` | (segredo) | embeddings e LLM reserva |
| `LLM_MODELOS` | a mesma lista do `.env` local | ordem da cadeia de LLMs |
| `API_KEYS` | (segredo novo, só da nuvem) | quem pode perguntar |
| `RATE_LIMIT_PERGUNTAS_POR_MINUTO` | `10` | protege a cota gratuita do Groq e do Gemini |
| `DEMO_PUBLICO` | `true` | visitante sem chave pergunta e vota (demo do README) |
| `RATE_LIMIT_DEMO_POR_MINUTO` | `3` | limite do visitante, contado por IP |
| `LIMITE_DIARIO_DEMO` | `100` | teto do dia somando todos os visitantes |

O resto (`RAG_EMBEDDING_MODEL`, `RAG_RERANKER_ATIVO`, `RAG_LIMIAR_DISTANCIA`,
`CHROMA_PATH`, `DATABASE_URL`, `CONFIAR_X_FORWARDED_FOR`) já vem do `Dockerfile.nuvem`.
Uma variável definida no painel vence a do Dockerfile.

Segredos nunca entram no Git: ficam só no `.env` local (ignorado) e no painel da Railway.

## Passo a passo (resumo)

1. Projeto novo a partir do repositório do GitHub; a Railway faz deploy a cada push na `main`.
2. Na API: variável `RAILWAY_DOCKERFILE_PATH=Dockerfile.nuvem`; no log do build deve aparecer
   `requirements-nuvem.txt`, e não `torch`.
3. Serviço `redis` a partir da imagem Docker `redis:7-alpine`.
4. Variáveis da tabela acima.
5. Volume na API, montado em `/data`.
6. Healthcheck em `/health/` e domínio público (Settings → Networking).
7. Enviar o corpus da máquina local, pela própria API:
   ```bash
   docker compose exec -e DOCASSIST_CHAVE="$(cat ~/.docassist_chave_nuvem)" api \
       python -m scripts.enviar_corpus --url https://SEU-APP.up.railway.app
   ```
   O `corpus/raw` não vai para o GitHub (licença CC BY-NC-SA dos documentos do Redis), então
   os documentos chegam como chegariam de um usuário: pelo `POST /rag/ingest`.
8. Abrir `https://SEU-APP.up.railway.app/chat` e perguntar. Com `DEMO_PUBLICO=true`, funciona
   sem chave, com os limites de visitante; com a chave de administração em 🔑, valem os
   limites normais.

## Simular a nuvem na máquina

```bash
docker compose -f docker-compose.yml -f docker-compose.nuvem.yml up -d --build api-nuvem
```

Sobe a imagem leve em `http://localhost:8001`, com `mem_limit: 512m`, SQLite e Chroma em
`./chroma_nuvem` (ignorada pelo Git).
