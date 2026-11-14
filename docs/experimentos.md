# Experimentos de recuperação

Cada experimento muda **uma** coisa em relação ao anterior, para mostrar o efeito de cada decisão.
Golden set: 20 perguntas (17 com resposta, 3 sem resposta). Corpus: 18 documentos de FastAPI,
Docker Compose, PostgreSQL e Redis. Relatórios completos em `evals/reports/`.

Todas as medições abaixo usam distância cosseno e busca exata (`hnsw:search_ef` = 200), o que
deixa os resultados idênticos entre execuções.

## Métricas

- **Por trecho:** o resultado contém a frase de evidência. É a métrica principal: na geração,
  o LLM recebe trechos, e a resposta depende de o trecho certo chegar até ele.
- **Por documento:** o resultado vem do documento certo. Permite comparar com o E0, em que cada
  documento inteiro era um único item.

## Resultados

| # | Configuração | R@1 trecho | R@3 trecho | R@5 trecho | MRR trecho | R@1 doc | R@5 doc | MRR doc |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| E0 | MiniLM, documento inteiro, só vetorial | 0,24 | 0,53 | 0,82 | 0,53 | 0,24 | 0,82 | 0,53 |
| E1 | + chunks por seção (250 tokens, overlap 30) | 0,12 | 0,29 | 0,41 | 0,24 | 0,41 | 0,71 | 0,58 |
| E2 | + embedding multilíngue (multilingual-e5-small) | 0,12 | 0,65 | 0,82 | 0,42 | 0,71 | 0,94 | 0,87 |
| E3 | + busca híbrida (BM25 + RRF) | | | | | | | |
| E4 | + reranker | | | | | | | |
| E5 | + limiar de relevância calibrado | | | | | | | |

Meta do escopo (O2): Recall@5 por trecho ≥ 0,85.

## Observações

### E0 — linha de base

- O MiniLM lê só os primeiros 256 tokens de cada texto: o vetor de um documento inteiro
  representa apenas o começo dele.
- Uma página genérica (`docker-compose-application-model`) ficou em 1º lugar em 7 perguntas,
  inclusive numa pergunta sem resposta: o vetor de um texto longo vira uma "média" de assuntos.
- Perguntas em português sem palavras em comum com o texto em inglês falham (q12 trouxe três
  documentos do PostgreSQL para uma pergunta sobre Redis).
- Com vetores normalizados, L2 e cosseno dão a mesma ordem. Confirmado na prática: refeito com
  cosseno, o E0 teve as mesmas posições, e as distâncias ficaram exatamente na metade
  (1,301 → 0,650), pois o Chroma devolve a L2 ao quadrado e, para vetores normalizados,
  L2² = 2 × (1 − cosseno).

### E1 — chunking

- 221 chunks; mediana de 157 tokens; nenhuma evidência cortada entre dois chunks.
- Por documento, o chunking ajudou: Recall@1 de 0,24 para 0,41 e MRR de 0,53 para 0,58.
- O Recall@5 por documento caiu (0,82 para 0,71): o mesmo documento passou a ocupar várias
  posições do top 5, deixando menos espaço para outros.
- Por trecho, a tarefa é muito mais difícil: achar 1 chunk entre 221, contra 1 documento entre 18.
- Os erros restantes são de busca, ligados principalmente ao idioma das perguntas (lacuna L3).
- **Reprodutibilidade:** com a busca aproximada padrão do Chroma, duas execuções do E1 deram
  números diferentes (R@3 por trecho 0,29 e 0,35). Corrigido com `hnsw:search_ef` = 200; os
  números da tabela são os da busca exata.

### E2 — modelo multilíngue

- Maior ganho até aqui: Recall@5 por trecho de 0,41 para 0,82 e Recall@1 por documento de 0,41
  para 0,71.
- O documento genérico deixou de dominar: q02, q06, q11 e q16 passaram a trazer o documento
  certo em 1º lugar.
- O Recall@1 por trecho não mudou (0,12): o documento certo vem em 1º, mas o chunk com a
  evidência costuma vir em 2º ou 3º, atrás de outro chunk do mesmo documento. Parte disso é
  limitação do golden set (uma só evidência por pergunta); o reranker deve ajudar.
- Erros restantes: q13 (descreve a ideia de injeção de dependências sem usar o termo), q12
  (confunde expiração com persistência) e q17 (precisa de dois documentos; o trecho do
  pg_isready não chega ao top 10).
- As distâncias do e5 ficam numa faixa estreita (0,10 a 0,18). Ainda assim, o maior valor entre
  as perguntas com resposta (0,169) ficou abaixo de duas das três perguntas sem resposta
  (0,172 e 0,182): primeiro sinal de que um limiar pode funcionar. A calibração fica para o E5,
  com mais perguntas sem resposta.
- No exercício de embeddings (`scripts/estudo_embeddings.py`), o e5 manteve a mesma separação
  entre frases relevantes e irrelevantes com a pergunta em português ou em inglês; o MiniLM não.

## Geração com citações (Fase 5)

Configuração: E2 (e5-small, chunks, busca exata), 5 trechos por pergunta, limiar de distância
0,17, cadeia de LLM `groq:openai/gpt-oss-120b` → `groq:qwen/qwen3.8-27b` →
`gemini:gemini-3.5-flash-lite`. Relatórios em `evals/reports/*_respostas_*.md`.

| Prompt | Respondidas | Respondeu e recusou quando devia | Falsa recusa | Recusou sem resposta | 2ª tentativa | Latência mediana |
| --- | --- | --- | --- | --- | --- | --- |
| answer_v1 | 14 de 20 | 17 de 20 | 3 de 17 (18%) | 3 de 3 | 5 | 1,66 s |
| answer_v2 | 16 de 20 | 19 de 20 | 1 de 17 (6%) | 3 de 3 | 0 | 1,25 s |

Metas do escopo: acerto em "sem resposta" ≥ 80% (atingida: 3 de 3); falsa recusa ≤ 10%
(atingida no v2: 6%).

### O que mudou do v1 para o v2

- Proibição explícita de acrescentar exemplos, comandos ou recomendações fora dos trechos.
- "Toda frase com informação técnica termina com a citação"; sem trecho para citar, não escrever.
- Responder primeiro o que foi perguntado (começar com "Sim" ou "Não" em perguntas de sim ou não).
- Um exemplo de formato com assunto fora do corpus (Git), para não contaminar a avaliação.

### Análise de erros

- **q12 (recuperação):** os 5 trechos vieram de `redis-persistence`; o modelo recusou
  corretamente. Depende de melhorar a busca (Fase 7).
- **q13:** recusada no v1 e respondida no v2 com os mesmos trechos. O trecho de dependências do
  FastAPI estava na 4ª posição; no v1 quem respondeu foi o modelo de reserva (qwen), que não o
  aproveitou. A cadeia de reserva garante resposta, mas o modelo de reserva pode ser menos capaz.
- **q02 (ambiguidade):** "o compose espera o banco ficar pronto?" foi lida como "consegue
  esperar?" e respondida com "Sim, com `service_healthy`"; a segunda frase traz o comportamento
  padrão correto. O prompt não foi ajustado só para essa pergunta, para não sobreajustar o
  sistema ao golden set. Fica para o juiz automático da Fase 8.
- **Formatação:** o modelo às vezes grudava a citação no fechamento de um bloco de código
  (```` ```[1] ````), o que quebra o Markdown. A validação de citações passou a mover a citação
  para a linha de baixo.
- **Latência:** a 1ª pergunta levava de 12 a 18 s porque carregava o modelo de embedding. A API
  passou a carregá-lo na inicialização (`RAG_AQUECER_MODELO`).
- **Cadeia de reserva:** o `gpt-oss-120b` atingiu o limite de tokens por minuto do Groq várias
  vezes durante o golden set (7 no v1, 4 no v2); o `qwen` assumiu sem nenhum erro para o usuário.
