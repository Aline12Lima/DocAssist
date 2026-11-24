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

Meta do escopo (O2): Recall@5 por trecho ≥ 0,85. Os experimentos seguintes (Fase 7) usam o
golden set ampliado para 60 perguntas: veja a seção "Fase 7".

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

## Fase 7 — golden set de 60 perguntas, busca híbrida e reranker

### Golden set ampliado

60 perguntas (50 com resposta, 10 sem resposta): factual 20, procedimento 15, termo exato 10,
dois documentos 5, sem resposta 10. Todos os 18 documentos têm pelo menos 2 perguntas. Com 20
perguntas, uma pergunta valia 6 pontos percentuais no Recall; com 60, vale menos de 2.

As perguntas sem resposta novas são do mesmo assunto do corpus (CORS no FastAPI, VACUUM no
PostgreSQL, limite de CPU no Compose), o que testa a recusa melhor que um assunto distante.

**Viés conhecido:** as 40 perguntas novas foram escritas lendo os documentos, e a redação delas
ficou mais próxima do texto. No E2, o Recall@1 por trecho foi 0,12 nas 20 antigas e 0,61 nas
novas; o Recall@5 foi 0,82 nos dois grupos. Por isso, a comparação entre experimentos vale; o
valor absoluto do Recall@1 superestima o desempenho com perguntas reais.

### Resultados (60 perguntas)

| # | Configuração | R@1 trecho | R@3 trecho | R@5 trecho | MRR trecho | Teto* | Reranker/pergunta |
| --- | --- | --- | --- | --- | --- | --- | --- |
| E2_60 | E2 (e5-small, chunks, só vetorial) | 0,44 | 0,74 | 0,82 | 0,63 | — | — |
| E3a | só BM25 | 0,28 | 0,42 | 0,56 | 0,39 | — | — |
| E3 | vetorial + BM25 com RRF (k = 60) | 0,38 | 0,58 | 0,64 | 0,53 | — | — |
| E4 | vetorial (30 candidatos) + reranker | 0,64 | 0,88 | **0,94** | 0,83 | 1,00 | 4,6 s |
| E4b | híbrida (até 60 candidatos) + reranker | 0,64 | 0,88 | 0,92 | 0,83 | 1,00 | 6,0 s |
| E4_c10 | vetorial (10 candidatos) + reranker | 0,62 | 0,82 | 0,86 | 0,79 | 0,88 | 1,3 s |
| E4_c15 | vetorial (15 candidatos) + reranker | 0,62 | 0,86 | 0,88 | 0,81 | 0,92 | 2,1 s |
| **E4_c20** | **vetorial (20 candidatos) + reranker** | 0,62 | 0,88 | **0,90** | 0,82 | 0,96 | 2,9 s |

\* Teto: fração das perguntas cujas evidências estão entre os candidatos. O reranker só
reordena; o que não está nos candidatos ele não recupera.

Reranker: `cross-encoder/mmarco-mMiniLMv2-L12-H384-v1` (multilíngue, treinado no mMARCO).
Tempos medidos na CPU do notebook de desenvolvimento.

Recall@5 por trecho, por tipo de pergunta:

| Tipo | E2_60 | E3a (BM25) | E3 (híbrida) | E4 (c30) | E4_c20 |
| --- | --- | --- | --- | --- | --- |
| termo exato | 0,80 | 0,90 | 0,90 | 1,00 | 1,00 |
| factual | 0,95 | 0,70 | 0,80 | 1,00 | 1,00 |
| procedimento | 0,73 | 0,33 | 0,40 | 1,00 | 0,93 |
| dois documentos | 0,60 | 0,00 | 0,20 | 0,40 | 0,20 |

### E3 — busca híbrida: não adotada

- A híbrida piorou o Recall@5 por trecho (0,82 → 0,64). Só ajudou em termos exatos (0,80 → 0,90).
- Causa: perguntas em português contra documentos em inglês têm poucas palavras em comum, só os
  termos técnicos (XX, GT, `service_healthy`, `pg_isready`). O BM25 sozinho chegou a 0,56.
- O RRF dá o mesmo peso às duas listas: os erros do BM25 empurraram para baixo resultados bons
  da busca vetorial (q09, q11 e q38 saíram do top 10). O documento longo
  `docker-compose-application-model` aparece no topo de quase toda pergunta de compose no BM25.
- Não testamos pesos diferentes no RRF: escolher o peso pelo melhor número nas mesmas 60
  perguntas seria sobreajustar ao conjunto de avaliação.
- Nem como fonte de candidatos para o reranker o BM25 ajudou (E4b): mesma qualidade, 30% mais
  lento, e uma pergunta sem resposta (q19) ganhou nota mais alta.
- O código (`lexical.py`, `hibrida.py`) fica no repositório, documentado, mas fora do `/rag/ask`.
  Com documentos e perguntas no mesmo idioma, a conclusão pode ser outra.

### E4 — reranker: adotado com 20 candidatos

- Maior ganho da Fase 7: Recall@5 por trecho de 0,82 para 0,94 com 30 candidatos. As perguntas
  que falhavam desde o E1 (q12, q13, q44, q46) entraram no top 5.
- Com 30 candidatos o teto foi 1,00: a busca vetorial já trazia o trecho certo, na posição
  errada. O reranker lê pergunta e trecho juntos e corrige a ordem.
- O custo cresce em linha reta com os candidatos (~140 ms por candidato nesta CPU). Escolha:
  **20 candidatos**, com Recall@5 0,90 (meta ≥ 0,85) e 2,9 s, contra 4,6 s com 30.
- Perguntas de dois documentos continuam difíceis (0,20 a 0,40): pedem as duas evidências no
  top 5, e o reranker tende a encher o topo com trechos do documento mais parecido.
- A nota do reranker separa as perguntas sem resposta muito melhor que a distância (E4_c20):
  média 6,22 nas com resposta contra −0,28 nas sem resposta; a maior nota de uma pergunta sem
  resposta foi 1,47 (q56). Com a distância, as faixas se sobrepunham (0,141 a 0,182 nas sem
  resposta; 0,098 a 0,189 nas com resposta).

### E5 — limiar pela nota do reranker

- Com o reranker ligado, a decisão de "não encontrei" sem chamar o LLM passa a usar a nota do
  melhor trecho, e não a distância: `RAG_LIMIAR_RERANKER` = 2,0.
- Escolha do valor: no E4_c20, as perguntas sem resposta ficaram todas abaixo de 1,5 e só duas
  com resposta abaixo de 2,0 (q13 com −0,78 e q27 com −0,10; a seguinte foi q53 com 2,52).
  O limiar fica no meio do intervalo vazio entre 1,47 e 2,52, e não no ponto que maximiza os
  acertos, para não depender demais destas 60 perguntas.
- Na recuperação, esse limiar daria 10 de 10 nas perguntas sem resposta e 2 de 50 (4%) de
  recusa indevida. O resultado de ponta a ponta, com o LLM, está na seção de geração abaixo.

### Geração de ponta a ponta com reranker (E5)

Configuração: E4_c20 (e5-small, 20 candidatos, reranker), limiar de nota 2,0, 5 trechos para
o LLM, prompt `answer_v2`, mesma cadeia de LLM da Fase 5. Relatório:
`evals/reports/2026-11-15_E5_respostas.md`.

| Rodada | Perguntas | Acerto sem resposta | Recusa indevida | Recusadas sem LLM | 2ª tentativa | Latência mediana | p95 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Fase 5 (E2, limiar de distância) | 20 | 3 de 3 | 1 de 17 (6%) | — | 0 | 1,25 s | — |
| **E5 (reranker, limiar de nota)** | 60 | **10 de 10 (100%)** | **3 de 50 (6%)** | 12 | 0 | 3,0 s | 8,2 s |

Metas do escopo atingidas: acerto em "sem resposta" ≥ 80% e recusa indevida ≤ 10%.

- **q12 resolvida:** era a única recusa indevida da Fase 5 (só trazia trechos de persistência);
  com o reranker, o trecho de EXPIRE chega ao LLM.
- **As 12 recusas sem LLM foram exatamente as previstas na recuperação:** as 10 sem resposta,
  q13 e q27. Na q13, a evidência não está entre os 20 candidatos (com 30 ela vinha em 1º).
  Na q27, o trecho certo vem em 1º, mas com nota −0,10: o reranker às vezes subestima um trecho
  certo, e o limiar transforma isso em recusa. É o custo de um limiar que recusa todas as
  perguntas sem resposta.
- **q51 (dois documentos):** recusada pelo próprio LLM. A evidência do TTL vem em 7º e não
  entra nos 5 trechos enviados; sem ela, o modelo não tinha como dizer como conferir o tempo
  restante. Recusar foi o comportamento correto; a falha é de recuperação, como nas outras
  perguntas de dois documentos.
- **Latência:** a mediana subiu de 1,25 s para 3,0 s; o reranker é a maior parte do tempo.
  O p95 de 8,2 s inclui as duas falhas de conexão com o Groq, em que a cadeia passou para o
  `qwen` sem erro para o usuário.
- **Pendências:** perguntas de dois documentos (diversificar os trechos enviados ao LLM) e
  latência (reranker mais leve ou quantizado; com pouca memória, `RAG_RERANKER_ATIVO=false`).

## Fase 9 — latência: de onde vem a espera

### Medição com o Prometheus (9.5)

15 perguntas do golden set pelo `/rag/ask/stream` (`scripts/gerar_trafego.py`), reranker com
20 candidatos. Medianas calculadas pelo Prometheus com `histogram_quantile`, que estima o
valor dentro da faixa do histograma (por isso são aproximadas):

| Etapa | Mediana | Parte do total |
| --- | --- | --- |
| busca (embedding da pergunta + Chroma) | 0,06 s | ~1% |
| **reranker** (20 pares pergunta-trecho) | **4,75 s** | **~80%** |
| LLM (texto inteiro, Groq) | 1,26 s | ~20% |
| até o 1º pedaço na tela | 5,3 s | — |
| total | 5,9 s | — |

p95 até o 1º pedaço: 10,4 s. Das 15 perguntas, 12 foram respondidas pelo LLM e 3 recusadas
pelo limiar do reranker, sem chamar o LLM.

- O gargalo é o reranker, não o LLM. Enquanto ele levar ~5 s, o streaming ajuda pouco: a
  pessoa espera olhando a tela parada e depois o texto chega quase de uma vez.
- O tempo do reranker varia com a carga da máquina: 2,9 s por pergunta no E4_c20 (14/11) e
  5,6 s no E6 (24/11), com a API, o Postgres, o Redis e o Prometheus rodando ao mesmo tempo.
  Comparações de tempo só valem medidas lado a lado, nas mesmas condições.

### E6 — reranker quantizado em int8: não adotado

Quantização dinâmica do PyTorch (`torch.quantization.quantize_dynamic`): os pesos das camadas
Linear passam de float32 para int8. Os dois modelos foram medidos um depois do outro, na mesma
máquina, com 20 candidatos:

| | float32 | int8 |
| --- | --- | --- |
| Recall@5 (trecho) | 0,90 | 0,88 |
| MRR (trecho) | **0,82** | **0,70** |
| Teto (candidatos) | 0,96 | 0,96 |
| Nota média do 1º, com resposta | 6,22 | 3,01 |
| Nota média do 1º, sem resposta | −0,28 | −1,86 |
| Tempo do reranker por pergunta | 5,6 s | **6,0 s** |

- Ficou **mais lento**, não mais rápido. A quantização dinâmica calcula a escala das ativações
  a cada chamada; num modelo pequeno (camadas de 384 dimensões), esse custo extra come o ganho
  da conta em int8. O ganho também depende de a CPU ter instruções para int8.
- A qualidade caiu: o MRR passou de 0,82 para 0,70, ou seja, o trecho certo desceu de posição.
- As notas mudaram de escala (média de 6,22 para 3,01). O limiar de 2,0 teria de ser calibrado
  de novo.
- Decisão: `RAG_RERANKER_QUANTIZADO=false`. O código fica no repositório, desligado e
  documentado. Quantizar não é uma otimização garantida: precisa ser medida.

## Fase 8 — juiz com LLM (correção e fidelidade das respostas)

Até a Fase 7, as métricas diziam se o trecho certo chegava ao LLM. Na Fase 8 um segundo LLM
(o juiz) avalia a resposta escrita, com duas notas de 0 a 2:

- **Correção:** a resposta diz o mesmo que a `resposta_referencia` do golden set?
- **Fidelidade:** tudo o que a resposta afirma está nos trechos que ela citou? Verdade que não
  está nos trechos não conta como fiel (é o que mede se o modelo inventou).

Juiz: `gemini-3.5-flash-lite` (reserva: `qwen3.8-27b`), de outra família que o modelo que
responde (`gpt-oss-120b`), porque LLMs tendem a favorecer textos parecidos com os seus.
Dois prompts: `judge_v1` (dá as notas direto) e `judge_v2` (lista cada afirmação da resposta,
marca se está nos trechos e só então dá as notas).

### Notas nas respostas reais

Respostas: `2026-11-15_F8_respostas` (mesma configuração do E5: 47 respondidas de 50).

| Juiz | Correção média | Correção 2 | Fidelidade média | Fidelidade 2 |
| --- | --- | --- | --- | --- |
| J1 (`judge_v1`) | 2,00 | 100% | 2,00 | 100% |
| J2 (`judge_v2`) | 2,00 | 100% | 1,98 | 98% (q14 com 1) |

### O juiz percebe erros? Teste com respostas estragadas de propósito

100% de nota máxima pode significar respostas ótimas ou um juiz que aprova tudo. Para separar
os dois casos, `evals/testar_juiz.py` sorteia 10 respostas reais e cria três versões com erros
conhecidos (`app/services/avaliacao/perturbacoes.py`):

| Versão | O que foi estragado | Esperado | judge_v1 | judge_v2 |
| --- | --- | --- | --- | --- |
| resposta trocada | resposta de outra pergunta, de outro documento | correção ≤ 1 e fidelidade ≤ 1 | 10 de 10 | 10 de 10 |
| afirmação inventada | resposta certa + frase inventada com citação [n] | fidelidade ≤ 1 | 10 de 10 (fid. média 0,40) | 10 de 10 (fid. média 0,10) |
| trechos trocados | resposta certa com os trechos de outra pergunta | fidelidade ≤ 1 | 10 de 10 | 10 de 10 |
| original | nada (controle) | — | 2,00 / 2,00 | 2,00 / 2,00 |

O teste foi rodado duas vezes com resultados praticamente iguais (o juiz é estável).

### Conclusões

- Os dois juízes perceberam os 30 erros, nas duas rodadas. A nota 100% das respostas reais não
  vem de um juiz que aprova tudo: no nível de erros grosseiros (resposta fora do assunto,
  informação inventada, citação que não sustenta o texto), as respostas do sistema estão boas.
- **Juiz padrão: `judge_v1`.** Uma frase inventada no fim da resposta é um detalhe secundário,
  e a regra pede fidelidade 1; o v1 seguiu melhor a regra (metade dos casos com 1), enquanto o
  v2 deu 0 em quase todos, mais severo do que a própria regra. O v1 também gasta menos tokens.
  O `judge_v2` continua disponível (`--versao judge_v2`) quando se quer a lista de afirmações
  para entender uma nota.
- Defeito conhecido: com uma afirmação inventada, os dois juízes também baixam a correção
  (média 1,1 a 1,6), embora o essencial da resposta continue certo. As duas notas não ficam
  totalmente independentes.
- Limite do teste: os erros criados são grosseiros. Erros sutis (por exemplo, uma afirmação que
  o trecho só faz para versões antigas do Redis, como na q05) podem passar despercebidos.

### Pendências

- **Calibração com notas humanas** (`evals/rotular.py` e `evals/medir_concordancia.py`):
  iniciada e adiada. As primeiras notas mostraram que a regra estava ambígua (tradução,
  paráfrase e respostas mais longas que a referência); a regra foi reescrita, mas as 15 notas
  ainda não foram dadas. É a forma de verificar os erros sutis.
- **q14**: única resposta com fidelidade 1 no `judge_v2`; ainda não foi lida para decidir se o
  juiz tem razão.
- **q02**: na Fase 5, a resposta começava com "Sim", e a referência diz que o compose não
  espera o banco por padrão. Os dois juízes deram correção 2; falta conferir a resposta atual.

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
