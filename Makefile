# Atalhos do DocAssist. Uso: make <alvo>

.PHONY: up down logs test corpus ingest eval

up:  ## Sobe a API, o Postgres e o Redis
	docker compose up -d

down:  ## Para tudo
	docker compose down

logs:  ## Acompanha os logs da API
	docker compose logs -f api

test:  ## Roda os testes dentro do container
	docker compose exec api sh -c "pip install --quiet pytest==8.2.0 && python -m pytest app/tests/"

corpus:  ## Baixa os documentos do manifesto
	docker compose exec api sh -c "python scripts/baixar_corpus.py && chown -R $$(id -u):$$(id -g) corpus/raw"

ingest:  ## Carrega o corpus na coleção principal do RAG
	docker compose exec api python -m scripts.ingerir_corpus

eval:  ## Avalia a recuperação com a configuração atual (E2)
	docker compose exec api sh -c "python -m evals.run_eval --nome E2 --modo chunks --modelo e5small && chown -R $$(id -u):$$(id -g) evals/reports"
