# Experimentos de recuperação

Cada experimento muda **uma** coisa em relação ao anterior, para mostrar o efeito de cada decisão.
Golden set: 20 perguntas (17 com resposta, 3 sem resposta). Corpus: 18 documentos de FastAPI,
Docker Compose, PostgreSQL e Redis. Relatórios completos em `evals/reports/`.

## Métricas

- **Por trecho:** o resultado contém a frase de evidência. É a métrica principal: na geração,
  o LLM recebe trechos, e a resposta depende de o trecho certo chegar até ele.
- **Por documento:** o resultado vem do documento certo. Permite comparar com o E0, em que cada
  documento inteiro era um único item.

## Resultados

| # | Configuração | R@1 trecho | R@3 trecho | R@5 trecho | MRR trecho | R@1 doc | R@5 doc | MRR doc |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| E0 | MiniLM, documento inteiro, só vetorial | 0,24 | 0,53 | 0,82 | 0,53 | 0,24 | 0,82 | 0,53 |
| E1 | + chunks por seção (250 tokens, overlap 30) | 0,12 | 0,35 | 0,41 | 0,25 | 0,41 | 0,71 | 0,59 |
| E2 | + embedding multilíngue | | | | | | | |
| E3 | + busca híbrida (BM25 + RRF) | | | | | | | |
| E4 | + reranker | | | | | | | |
| E5 | + limiar de relevância calibrado | | | | | | | |

## Observações

### E0 — linha de base (2026-11-10)

- O modelo lê só os primeiros 256 tokens de cada texto: o vetor de um documento inteiro
  representa apenas o começo dele.
- Uma página genérica (`docker-compose-application-model`) ficou em 1º lugar em 7 perguntas,
  inclusive numa pergunta sem resposta: o vetor de um texto longo vira uma "média" de assuntos.
- Perguntas em português sem palavras em comum com o texto em inglês falham (q12 trouxe três
  documentos do PostgreSQL para uma pergunta sobre Redis).
- O "não encontrei" ainda não é possível: perguntas sem resposta tiveram distâncias menores que
  várias perguntas com resposta.
- Este modelo gera vetores normalizados, então L2 e cosseno dão a mesma ordem de resultados
  (cosseno = 1 − distância L2 ÷ 2).

### E1 — chunking (2026-11-12)

- 221 chunks; mediana de 157 tokens; nenhuma evidência cortada entre dois chunks.
- Por documento, o chunking ajudou: Recall@1 de 0,24 para 0,41 e MRR de 0,53 para 0,59.
- O Recall@5 por documento caiu (0,82 para 0,71): o mesmo documento passou a ocupar várias
  posições do top 5, deixando menos espaço para outros.
- Por trecho, a tarefa é muito mais difícil: achar 1 chunk entre 221, contra 1 documento entre 18.
- Todas as respostas estão inteiras em algum chunk: os erros restantes são de busca, ligados
  principalmente ao idioma das perguntas (lacuna L3).
- **Reprodutibilidade:** duas execuções do E1 deram números diferentes (R@3 por trecho 0,29 e
  0,35). Causa: a busca aproximada do índice HNSW do Chroma, que examina poucos candidatos por
  padrão. Correção prevista na Fase 4 (`hnsw:search_ef` maior), com nova medição do E0 e do E1.
