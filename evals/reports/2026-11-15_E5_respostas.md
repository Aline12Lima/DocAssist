# Respostas do golden set (2026-11-15)

## Resumo

- Prompt: answer_v2
- Busca: vetorial + reranker `cross-encoder/mmarco-mMiniLMv2-L12-H384-v1` (20 candidatos, limiar de nota 2.0)
- Respondidas: 47 de 60
- Respondeu quando devia e recusou quando devia: 57 de 60
- Acerto nas perguntas sem resposta: 10 de 10 (100%)
- Recusa indevida (devia responder e não respondeu): 3 de 50 (6%)
- Recusadas pelo limiar, sem chamar o LLM: 12
- Precisou de 2ª tentativa (sem citação na 1ª): 0
- Latência com LLM: mediana 3047 ms, p95 8217 ms
- Latência de todas as perguntas: mediana 2899 ms, p95 8217 ms
- Modelos usados: {'groq:openai/gpt-oss-120b': 46, 'nenhum': 12, 'groq:qwen/qwen3.8-27b': 2}

## q01 — O que o comando TTL do Redis retorna para uma chave que existe mas não tem expiração?

*Tipo: factual · deve responder · referência: Retorna -1.*

Retorna `-1` quando a chave existe, mas não possui expiração associada[1].

**Fontes:**
- [1] Redis — TTL (distância 0.1031, nota 10.82)

`modelo: groq:openai/gpt-oss-120b | tokens: 1284+132 | tentativas: 1 | 10203 ms`

## q02 — O docker compose espera o banco de dados ficar pronto antes de iniciar a API?

*Tipo: factual · deve responder · referência: Não. Ele só espera o container estar rodando; para esperar ficar pronto, é preciso usar condition: service_healthy com um healthcheck.*

Não. Por padrão o Docker Compose só aguarda que o contêiner esteja em execução, não que ele esteja “pronto” — por exemplo, que o banco de dados já aceite conexões [1]. Para que o Compose espere o banco ficar saudável antes de iniciar a API, é preciso usar `depends_on` com a opção `condition: service_healthy` e definir um `healthcheck` no serviço do banco, como no exemplo abaixo [4].

**Fontes:**
- [1] Docker Compose — Control startup and shutdown order › Control startup (distância 0.1495, nota 5.23)
- [4] Docker Compose — Control startup and shutdown order › Example (distância 0.1501, nota 0.74)

`modelo: groq:openai/gpt-oss-120b | tokens: 1271+430 | tentativas: 1 | 3988 ms`

## q03 — No FastAPI, como os parâmetros de query aparecem na URL?

*Tipo: factual · deve responder · referência: São pares chave-valor depois do ? na URL, separados por &.*

No FastAPI, os parâmetros de query são incluídos na URL após o caractere `?`, como pares `chave=valor` separados por `&`. Por exemplo:

```
http://127.0.0.1:8000/items/?skip=0&limit=10
```

[1]

**Fontes:**
- [1] FastAPI — Query Parameters › Query Parameters (distância 0.1161, nota 8.33)

`modelo: groq:openai/gpt-oss-120b | tokens: 1332+204 | tentativas: 1 | 2636 ms`

## q04 — Como configurar um Ingress no Kubernetes?

*Tipo: sem_resposta · NÃO deve responder · referência: Não está nos documentos.*

Não encontrei essa informação nos documentos carregados.

> Aviso: Trechos mais próximos, abaixo do limiar de relevância.

**Trechos mais próximos:**
- [1] Docker Compose — Networking › Default network and service discovery (distância 0.1964, nota -1.51)
- [2] Docker Compose — Networking › Debugging (distância 0.1913, nota -2.04)
- [3] Docker Compose — Control startup and shutdown order › Example (distância 0.1881, nota -3.28)

`modelo: None | tokens: 0+0 | tentativas: 0 | 1771 ms`

## q05 — Qual a diferença entre a persistência RDB e a AOF no Redis?

*Tipo: factual · deve responder · referência: O RDB salva fotos (snapshots) dos dados em intervalos definidos; o AOF registra cada operação de escrita e a reexecuta quando o servidor reinicia.*

RDB e AOF são os dois modos principais de persistência do Redis, e eles funcionam de forma diferente:

* **RDB** cria snapshots pontuais do dataset em intervalos definidos, gerando um único arquivo compacto. Esse arquivo é ideal para backups, recuperação de desastres e transferências para outros data‑centers ou serviços como S3. Como a persistência é feita por um processo filho, o processo principal do Redis não realiza I/O de disco, o que maximiza a performance e permite reinicializações mais rápidas, especialmente em bases de dados grandes. Também facilita a restauração de versões diferentes do dataset e suporta ressincronizações parciais em réplicas após falhas. [4][1]

* **AOF** registra **todas** as operações de escrita recebidas pelo servidor, usando o mesmo formato do protocolo Redis. Na reinicialização, o AOF é usado para reconstruir o dataset porque contém o histórico mais completo. Contudo, os arquivos AOF costumam ser maiores que os RDB e podem ser mais lentos, dependendo da política de `fsync` (por exemplo, com `fsync` a cada segundo ainda há bom desempenho, mas sem `fsync` pode ser tão rápido quanto RDB). Em versões < 7.0, durante a reescrita do AOF, as escritas são armazenadas em memória e depois gravadas duas vezes, o que pode consumir muita memória e até congelar o processo de escrita. [1][3][2]

**Fontes:**
- [1] Redis — Persistence (distância 0.102, nota 10.27)
- [2] Redis — Persistence › Interactions between AOF and RDB persistence (distância 0.0975, nota 10.25)
- [3] Redis — Persistence › AOF disadvantages (distância 0.1051, nota 8.98)
- [4] Redis — Persistence › RDB advantages (distância 0.1179, nota 7.81)

`modelo: groq:openai/gpt-oss-120b | tokens: 1381+446 | tentativas: 1 | 3047 ms`

## q06 — Como os containers de um mesmo projeto do compose se encontram na rede?

*Tipo: factual · deve responder · referência: Pelo nome do serviço: cada serviço registra o nome num DNS interno da rede padrão do projeto.*

Os containers de um mesmo projeto do Compose são conectados ao **network default** que o Compose cria (chamado `<project-name>_default`). Cada container entra nesse network, registra seu nome em um servidor DNS interno e, assim, pode ser alcançado pelos demais containers usando apenas o **nome do serviço** – sem necessidade de IPs ou configuração manual [1].

**Fontes:**
- [1] Docker Compose — Networking › Default network and service discovery (distância 0.1738, nota 4.55)

`modelo: groq:openai/gpt-oss-120b | tokens: 1160+218 | tentativas: 1 | 2670 ms`

## q07 — Como o docker compose define o nome do projeto quando nenhum nome é informado?

*Tipo: factual · deve responder · referência: Usa o nome da pasta onde está o arquivo do compose.*

Ele usa o nome do diretório que contém o arquivo `compose.yaml` como nome do projeto por padrão [3][5].

**Fontes:**
- [3] Docker Compose — Specify a project name (distância 0.1593, nota 5.09)
- [5] Docker Compose — Networking › Default network and service discovery (distância 0.1705, nota 2.08)

`modelo: groq:openai/gpt-oss-120b | tokens: 1213+208 | tentativas: 1 | 2172 ms`

## q08 — No PostgreSQL, qual tipo de texto é mais rápido: char(n), varchar(n) ou text?

*Tipo: factual · deve responder · referência: Não há diferença relevante de desempenho; o char(n) costuma ser o mais lento por ocupar mais espaço.*

Não há diferença de desempenho entre os tipos `char(n)`, `varchar(n)` e `text`; na prática `text` ou `varchar` são tão rápidos quanto, enquanto `char(n)` costuma ser o mais lento devido ao custo extra de armazenamento [1].

**Fontes:**
- [1] PostgreSQL 16 — Character Types › 8.3. Character Types # › Tip (distância 0.1232, nota 4.83)

`modelo: groq:openai/gpt-oss-120b | tokens: 1239+312 | tentativas: 1 | 2937 ms`

## q09 — Como escrever testes automatizados para uma API feita com FastAPI?

*Tipo: procedimento · deve responder · referência: Criar um TestClient passando a aplicação, escrever funções com nome começando em test_ e usar assert com o pytest.*

Para testar uma API FastAPI de forma automatizada:

1. **Instale as dependências de teste**  
   - Adicione o cliente HTTP usado pelos testes: `httpx` [1].  
   - Instale o framework de testes: `pytest` [2].

2. **Crie um arquivo de testes**  
   - Normalmente um arquivo como `test_main.py` fica ao lado do código da aplicação, dentro do mesmo pacote (ex.: `app/test_main.py`) [3][5].

3. **Importe a aplicação e crie um `TestClient`**  
   ```python
   from fastapi import FastAPI
   from fastapi.testclient import TestClient   # ou `from starlette.testclient import TestClient` [1]
   from .main import app                       # import relativo porque o teste está no mesmo pacote [3]

   client = TestClient(app)                    # passa a aplicação FastAPI ao cliente [1]
   ```

4. **Escreva funções de teste**  
   - Cada teste deve ser uma função normal (`def`) cujo nome começa com `test_` [1].  
   - Use chamadas síncronas ao cliente (sem `await`) [1].  
   - Verifique o comportamento com `assert` usando expressões Python padrão [1].

   ```python
   def test_root():
       response = client.get("/")               # chamada normal, não assíncrona
       assert response.status_code == 200
       assert response.json() == {"message": "Hello World"}
   ```

5. **Execute os testes**  
   - Rode `pytest` (por exemplo, `uv run pytest`) [2]; o framework detecta automaticamente os arquivos e funções de teste e reporta os resultados [2].

Seguindo esses passos – instalar `httpx` e `pytest`, colocar os testes em arquivos como `test_*.py` no mesmo pacote, usar `TestClient` para chamar a API e validar as respostas com `assert` – você terá testes automatizados para sua API FastAPI.

**Fontes:**
- [1] FastAPI — Testing › Testing › Using `TestClient` (distância 0.131, nota 6.46)
- [2] FastAPI — Testing › Testing › Run it (distância 0.1245, nota 5.28)
- [3] FastAPI — Testing › Testing › Separating tests › Testing file (distância 0.1492, nota 4.86)
- [5] FastAPI — Testing › Testing › Separating tests (distância 0.1576, nota 3.35)

`modelo: groq:openai/gpt-oss-120b | tokens: 1224+700 | tentativas: 1 | 4609 ms`

## q10 — Como recebo dados em JSON no corpo de uma requisição no FastAPI?

*Tipo: procedimento · deve responder · referência: Declarando um modelo Pydantic (classe que herda de BaseModel) e usando-o como tipo de um parâmetro da função.*

Para receber JSON no corpo da requisição, crie um modelo Pydantic herdando de `BaseModel` (importando‑o de `pydantic`) e declare os atributos com tipos Python padrão [2].  
Em seguida, na sua *path operation*, declare um parâmetro do tipo desse modelo; FastAPI lerá o corpo da requisição como JSON, converterá os tipos, validará os dados e disponibilizará o conteúdo no parâmetro [1][5].

**Fontes:**
- [1] FastAPI — Request Body › Request Body (distância 0.1264, nota 9.52)
- [2] FastAPI — Request Body › Request Body (distância 0.1346, nota 7.5)
- [5] FastAPI — Request Body › Request Body › Request body + path + query parameters (distância 0.1306, nota 4.45)

`modelo: groq:openai/gpt-oss-120b | tokens: 1350+430 | tentativas: 1 | 4126 ms`

## q11 — Como definir variáveis de ambiente para um serviço no docker compose?

*Tipo: procedimento · deve responder · referência: Com o atributo environment no serviço (em lista ou mapa) ou com o atributo env_file apontando para um arquivo .env.*

Use o atributo **`environment`** no `compose.yaml` do serviço, informando as variáveis diretamente.  
Ele aceita sintaxe de mapeamento:

```yaml
services:
  webapp:
    environment:
      DEBUG: "true"
```

ou sintaxe de lista, que equivale ao exemplo acima:

```yaml
services:
  webapp:
    environment:
      - DEBUG=true
```
[1]

Outra opção é carregar variáveis a partir de arquivos `.env` com o atributo **`env_file`**, que pode apontar para um ou mais arquivos:

```yaml
services:
  webapp:
    env_file: "webapp.env"
```
[3]

> ⚠️ Não use variáveis de ambiente para informações sensíveis (senhas, chaves, etc.); prefira **secrets**.  
[2]

**Fontes:**
- [1] Docker Compose — Set environment variables › Use the `environment` attribute (distância 0.1319, nota 10.13)
- [2] Docker Compose — Set environment variables (distância 0.139, nota 9.36)
- [3] Docker Compose — Set environment variables › Use the `env_file` attribute (distância 0.1524, nota 8.48)

`modelo: groq:openai/gpt-oss-120b | tokens: 999+375 | tentativas: 1 | 2902 ms`

## q12 — Como fazer uma chave do Redis ser apagada sozinha depois de um tempo?

*Tipo: procedimento · deve responder · referência: Usando o comando EXPIRE com a chave e o tempo em segundos.*

Use o comando da família **EXPIRE** para associar um tempo de vida (TTL) à chave.  
Exemplo:

```redis
EXPIRE minhaChave 300   # a chave será removida automaticamente em 300 s
```

Ao definir um timeout, a chave passa a ser considerada *volátil* e será excluída assim que o tempo especificado expirar [3]. O mesmo efeito pode ser obtido com os comandos relacionados (`PEXPIRE`, `EXPIREAT`, etc.), que também permitem atualizar ou remover o TTL usando `PERSIST` [2][3].

**Fontes:**
- [2] Redis — EXPIRE › Details › Appendix: Redis expires (distância 0.1751, nota 3.23)
- [3] Redis — EXPIRE (distância 0.1721, nota 3.09)

`modelo: groq:openai/gpt-oss-120b | tokens: 1406+314 | tentativas: 1 | 3310 ms`

## q13 — Como reaproveitar a mesma lógica, como a conexão com o banco, em várias rotas do FastAPI?

*Tipo: procedimento · deve responder · referência: Usando o sistema de injeção de dependências do FastAPI: uma função de dependência declarada com Depends nas rotas.*

Não encontrei essa informação nos documentos carregados.

> Aviso: Trechos mais próximos, abaixo do limiar de relevância.

**Trechos mais próximos:**
- [1] FastAPI — Path Parameters › Path Parameters › Data validation (distância 0.1644, nota -0.78)
- [2] FastAPI — Dependencies › Dependencies › First Steps › Declare the dependency, in the "dependant" (distância 0.1663, nota -0.98)
- [3] FastAPI — Dependencies › Dependencies › First Steps (distância 0.1609, nota -1.27)

`modelo: None | tokens: 0+0 | tentativas: 0 | 2747 ms`

## q14 — Para que serve o pg_isready?

*Tipo: termo_exato · deve responder · referência: Verifica se o servidor PostgreSQL está aceitando conexões; o código de saída indica o resultado.*

O `pg_isready` é uma utilidade que verifica o status de conexão de um servidor PostgreSQL, indicando se ele está aceitando conexões, rejeitando‑as ou não respondendo [1][3].

**Fontes:**
- [1] PostgreSQL 16 — pg_isready (distância 0.1231, nota 8.83)
- [3] PostgreSQL 16 — pg_isready (distância 0.136, nota 1.9)

`modelo: groq:openai/gpt-oss-120b | tokens: 1139+93 | tentativas: 1 | 2393 ms`

## q15 — O que faz a opção NX do comando EXPIRE do Redis?

*Tipo: termo_exato · deve responder · referência: Só define a expiração se a chave ainda não tiver uma.*

A opção **NX** faz com que o tempo de expiração seja definido **apenas quando a chave ainda não possui um expiry** [1].

**Fontes:**
- [1] Redis — EXPIRE (distância 0.148, nota 5.76)

`modelo: groq:openai/gpt-oss-120b | tokens: 1142+127 | tentativas: 1 | 2278 ms`

## q16 — No compose, um serviço fala com outro pela HOST_PORT ou pela CONTAINER_PORT?

*Tipo: termo_exato · deve responder · referência: Pela CONTAINER_PORT. A porta do host só é usada para acessar o serviço de fora da rede.*

Usa a **CONTAINER_PORT**; a porta do host (HOST_PORT) serve apenas para acesso externo à rede. [2]

**Fontes:**
- [2] Docker Compose — Networking › Default network and service discovery (distância 0.1615, nota 1.42)

`modelo: groq:openai/gpt-oss-120b | tokens: 1294+197 | tentativas: 1 | 2709 ms`

## q17 — Como fazer a API esperar o Postgres estar pronto para conexões no docker compose?

*Tipo: dois_docs · deve responder · referência: Definir um healthcheck no serviço do Postgres com pg_isready e usar depends_on com condition: service_healthy na API.*

Use o `depends_on` com a condição **`service_healthy`** e defina um *healthcheck* no serviço do PostgreSQL que utilize `pg_isready`. Assim o serviço da API só será criado depois que o container do Postgres for considerado “healthy”.  

Exemplo (extraído dos trechos):

```yaml
services:
  web:               # sua API
    build: .
    depends_on:
      db:
        condition: service_healthy   # aguarda o Postgres saudável
        restart: true                # opcional: reinicia a API se o DB for reiniciado
  db:                # PostgreSQL
    image: postgres:18
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U $${POSTGRES_USER} -d $${POSTGRES_DB}"]
      interval: 10s
      retries: 5
      start_period: 30s
      timeout: 10s
```

- O `condition: service_healthy` faz o Compose esperar o *healthcheck* do `db` passar antes de iniciar o `web` [1][3].  
- O *healthcheck* usa o comando `pg_isready` para verificar se o PostgreSQL está pronto para aceitar conexões [2].  

Com essa configuração a API só iniciará quando o Postgres estiver pronto.

**Fontes:**
- [1] Docker Compose — Control startup and shutdown order › Control startup (distância 0.1588, nota 2.74)
- [2] Docker Compose — Control startup and shutdown order › Example (distância 0.147, nota 2.49)
- [3] Docker Compose — Control startup and shutdown order › Example (distância 0.1487, nota 1.32)

`modelo: groq:openai/gpt-oss-120b | tokens: 1256+535 | tentativas: 1 | 8217 ms`

## q18 — Por que a rede criada pelo compose do projeto se chama docassist_default?

*Tipo: dois_docs · deve responder · referência: O nome do projeto vem da pasta (DocAssist, em minúsculas), e a rede padrão se chama <nome-do-projeto>_default.*

Porque, por padrão, o Docker Compose cria uma rede única para o aplicativo e a nomeia como `<nome‑do‑projeto>_default`. Quando o projeto se chama **docassist**, a rede gerada passa a ser **docassist_default** [1][2].

**Fontes:**
- [1] Docker Compose — Networking › Default network and service discovery (distância 0.1666, nota 5.01)
- [2] Docker Compose — Networking › Default network and service discovery (distância 0.1672, nota 1.06)

`modelo: groq:openai/gpt-oss-120b | tokens: 1340+175 | tentativas: 1 | 2735 ms`

## q19 — Como configurar autenticação com OAuth2 e tokens JWT no FastAPI?

*Tipo: sem_resposta · NÃO deve responder · referência: Não está nos documentos carregados.*

Não encontrei essa informação nos documentos carregados.

> Aviso: Trechos mais próximos, abaixo do limiar de relevância.

**Trechos mais próximos:**
- [1] FastAPI — Request Body › Request Body (distância 0.1621, nota -0.43)
- [2] FastAPI — Path Parameters › Path Parameters › Predefined values › Working with Python *enumerations* (distância 0.1705, nota -0.66)
- [3] FastAPI — Request Body › Request Body › Request body + path + query parameters (distância 0.1751, nota -0.7)

`modelo: None | tokens: 0+0 | tentativas: 0 | 2882 ms`

## q20 — Como fazer backup de um banco MongoDB?

*Tipo: sem_resposta · NÃO deve responder · referência: Não está nos documentos.*

Não encontrei essa informação nos documentos carregados.

> Aviso: Trechos mais próximos, abaixo do limiar de relevância.

**Trechos mais próximos:**
- [1] Redis — Persistence › Backing up Redis data (distância 0.1802, nota -1.27)
- [2] Redis — Persistence › Backing up Redis data › Online backups with the BACKUP command family (distância 0.1715, nota -1.88)
- [3] Redis — Persistence › Disaster recovery (distância 0.1921, nota -1.99)

`modelo: None | tokens: 0+0 | tentativas: 0 | 1831 ms`

## q21 — O que o FastAPI gera automaticamente a partir das rotas usando o padrão OpenAPI?

*Tipo: factual · deve responder · referência: Um schema de toda a API no padrão OpenAPI, usado pela documentação automática.*

O FastAPI gera automaticamente um **esquema OpenAPI em formato JSON** (acessível em `/openapi.json`) que descreve todas as rotas da aplicação, seus parâmetros, respostas etc. Esse esquema alimenta a documentação interativa incluída (Swagger UI em `/docs` e ReDoc em `/redoc`) [1][5]

**Fontes:**
- [1] FastAPI — First Steps › First Steps (distância 0.1371, nota 4.18)
- [5] FastAPI — Path Parameters › Path Parameters › Documentation (distância 0.1499, nota 1.27)

`modelo: groq:openai/gpt-oss-120b | tokens: 1196+396 | tentativas: 1 | 4275 ms`

## q22 — A classe FastAPI herda de qual outra classe?

*Tipo: factual · deve responder · referência: De Starlette.*

Sim. A classe `FastAPI` herda diretamente de `Starlette` [1].

**Fontes:**
- [1] FastAPI — First Steps › First Steps › Recap, step by step › Step 1: import `FastAPI` (distância 0.1403, nota 4.23)

`modelo: groq:qwen/qwen3.8-27b | tokens: 1106+20 | tentativas: 1 | 8274 ms`

## q23 — Se a rota declara item_id: int e eu acesso /items/3, a função recebe o valor como texto ou como inteiro?

*Tipo: factual · deve responder · referência: Como inteiro (int) do Python, não como string.*

Sim. A função recebe o valor como um inteiro Python (`int`), não como texto [string] [1].

**Fontes:**
- [1] FastAPI — Path Parameters › Path Parameters › Data conversion (distância 0.1627, nota 3.57)

`modelo: groq:openai/gpt-oss-120b | tokens: 1175+137 | tentativas: 1 | 3593 ms`

## q24 — Qual biblioteca faz a validação dos dados dos parâmetros por baixo dos panos no FastAPI?

*Tipo: factual · deve responder · referência: O Pydantic.*

Pydantic realiza a validação dos dados dos parâmetros por baixo dos panos no FastAPI [1].

**Fontes:**
- [1] FastAPI — Path Parameters › Path Parameters › Pydantic (distância 0.1469, nota 4.32)

`modelo: groq:openai/gpt-oss-120b | tokens: 1283+106 | tentativas: 1 | 3121 ms`

## q25 — Qual é o nome padrão do arquivo de configuração do Docker Compose?

*Tipo: factual · deve responder · referência: compose.yaml (preferido) ou compose.yml, no diretório de trabalho.*

O nome padrão do arquivo de configuração do Docker Compose é `compose.yaml` (preferencial), podendo também ser `compose.yml` [2].

**Fontes:**
- [2] Docker Compose — How Compose works › The Compose file (distância 0.1278, nota 6.04)

`modelo: groq:openai/gpt-oss-120b | tokens: 1237+197 | tentativas: 1 | 2502 ms`

## q26 — O que é um sorted set no Redis?

*Tipo: factual · deve responder · referência: Uma coleção de strings únicas ordenadas pelo score associado a cada uma.*

Um sorted set no Redis é uma coleção de strings únicas que mantêm a ordem com base em um “score” associado a cada string[1].

**Fontes:**
- [1] Redis — Data types › Data types (distância 0.108, nota 10.58)

`modelo: groq:openai/gpt-oss-120b | tokens: 1079+84 | tentativas: 1 | 2454 ms`

## q27 — Qual o custo de verificar se um elemento existe em um set do Redis?

*Tipo: factual · deve responder · referência: O(1): constante, independe do número de elementos.*

Não encontrei essa informação nos documentos carregados.

> Aviso: Trechos mais próximos, abaixo do limiar de relevância.

**Trechos mais próximos:**
- [1] Redis — Data types › Data types › Sets (distância 0.1386, nota -0.1)
- [2] Redis — Data types › Data types › Cuckoo filter (distância 0.1615, nota -0.14)
- [3] Redis — Data types › Data types (distância 0.1567, nota -0.98)

`modelo: None | tokens: 0+0 | tentativas: 0 | 1663 ms`

## q28 — No PostgreSQL, a tabela continua aceitando INSERT e UPDATE enquanto um índice está sendo criado?

*Tipo: factual · deve responder · referência: Por padrão não: leituras continuam, mas escritas ficam bloqueadas até o índice terminar.*

Não. Por padrão, o PostgreSQL bloqueia operações de escrita (INSERT, UPDATE, DELETE) enquanto o índice está sendo criado; apenas leituras (SELECT) podem ocorrer em paralelo. Para permitir escritas simultâneas é necessário criar o índice de forma concorrente [2].

**Fontes:**
- [2] PostgreSQL 16 — Indexes: Introduction › 11.1. Introduction # (distância 0.1402, nota 6.44)

`modelo: groq:openai/gpt-oss-120b | tokens: 1435+268 | tentativas: 1 | 3444 ms`

## q29 — Qual é o tamanho máximo de uma string que o PostgreSQL consegue armazenar?

*Tipo: factual · deve responder · referência: Cerca de 1 GB.*

O tamanho máximo de uma string que o PostgreSQL pode armazenar é de aproximadamente 1 GB [1].

**Fontes:**
- [1] PostgreSQL 16 — Character Types › 8.3. Character Types # (distância 0.1246, nota 4.63)

`modelo: groq:openai/gpt-oss-120b | tokens: 1413+180 | tentativas: 1 | 2319 ms`

## q30 — No Redis, os arquivos AOF costumam ser maiores ou menores que os arquivos RDB?

*Tipo: factual · deve responder · referência: Maiores, para o mesmo conjunto de dados.*

Os arquivos AOF costumam ser maiores que os arquivos RDB equivalentes para o mesmo conjunto de dados [1].

**Fontes:**
- [1] Redis — Persistence › AOF disadvantages (distância 0.1266, nota 10.53)

`modelo: groq:openai/gpt-oss-120b | tokens: 1391+124 | tentativas: 1 | 6457 ms`

## q31 — É recomendado passar senhas por variáveis de ambiente no docker compose?

*Tipo: factual · deve responder · referência: Não; a documentação recomenda usar secrets.*

Não. Não se recomenda usar variáveis de ambiente para passar informações sensíveis, como senhas, para os containers; deve‑se usar *secrets* em vez disso [2].

**Fontes:**
- [2] Docker Compose — Set environment variables (distância 0.1447, nota 5.36)

`modelo: groq:openai/gpt-oss-120b | tokens: 1040+124 | tentativas: 1 | 2899 ms`

## q32 — O que acontece com o IP de um container quando o compose o recria após uma mudança de configuração?

*Tipo: factual · deve responder · referência: O container antigo é removido e o novo entra na rede com outro IP, mas com o mesmo nome.*

Quando o Compose recria um container após uma mudança de configuração, ele recebe um novo endereço IP, porém o nome do serviço permanece estável [1][3].

**Fontes:**
- [1] Docker Compose — Networking › Default network and service discovery (distância 0.1627, nota 4.97)
- [3] Docker Compose — Networking › Default network and service discovery (distância 0.1568, nota 3.49)

`modelo: groq:openai/gpt-oss-120b | tokens: 1359+254 | tentativas: 1 | 3334 ms`

## q33 — No FastAPI, uma dependência pode ter suas próprias dependências?

*Tipo: factual · deve responder · referência: Sim, o sistema de dependências é hierárquico.*

Sim. No FastAPI, uma dependência pode ter suas próprias dependências, formando uma árvore hierárquica de dependências que o sistema resolve automaticamente [1].

**Fontes:**
- [1] FastAPI — Dependencies › Dependencies › Simple and Powerful (distância 0.1583, nota 4.71)

`modelo: groq:openai/gpt-oss-120b | tokens: 999+129 | tentativas: 1 | 3684 ms`

## q34 — Como rodar o servidor de desenvolvimento de uma aplicação FastAPI?

*Tipo: procedimento · deve responder · referência: Com o comando fastapi dev.*

Use o comando `fastapi dev` para iniciar o servidor de desenvolvimento [1][2].

**Fontes:**
- [1] FastAPI — First Steps › First Steps › Recap (distância 0.1181, nota 9.81)
- [2] FastAPI — First Steps › First Steps (distância 0.1255, nota 9.51)

`modelo: groq:openai/gpt-oss-120b | tokens: 1340+178 | tentativas: 1 | 3402 ms`

## q35 — Como restringir um parâmetro de rota do FastAPI a uma lista fixa de valores aceitos?

*Tipo: procedimento · deve responder · referência: Declarando o tipo do parâmetro como uma classe Enum do Python.*

Use um `Enum` Python para definir os valores permitidos e anote o parâmetro da rota com esse enum.

```python
from enum import Enum
from fastapi import FastAPI

class ModelName(str, Enum):
    alexnet = "alexnet"
    resnet = "resnet"
    lenet = "lenet"

app = FastAPI()

@app.get("/models/{model_name}")
def read_model(model_name: ModelName):
    return {"model_name": model_name}
```

1. Crie uma classe que herde de `str` e `Enum` para que o Swagger reconheça os valores como strings [2].  
2. Defina os atributos da classe com os valores fixos que serão aceitos [2].  
3. Declare o parâmetro da rota usando a anotação do enum [3]; assim o FastAPI aceita apenas os valores definidos.  

O valor recebido será um membro da enumeração, podendo ser comparado ou convertido para a string com `model_name.value` [4].

**Fontes:**
- [2] FastAPI — Path Parameters › Path Parameters › Predefined values (distância 0.162, nota 0.95)
- [3] FastAPI — Path Parameters › Path Parameters › Predefined values (distância 0.1624, nota 0.14)
- [4] FastAPI — Path Parameters › Path Parameters › Predefined values › Working with Python *enumerations* (distância 0.165, nota 0.12)

`modelo: groq:openai/gpt-oss-120b | tokens: 1148+350 | tentativas: 1 | 4473 ms`

## q36 — Como deixar um parâmetro de query opcional no FastAPI?

*Tipo: procedimento · deve responder · referência: Definindo o valor padrão como None.*

Para tornar um parâmetro de query opcional, basta declarar o parâmetro na função com o valor padrão `None`. Assim o FastAPI o reconhece como um parâmetro de query opcional, que receberá `None` quando não for informado na URL.  

Exemplo:

```python
from fastapi import FastAPI

app = FastAPI()

@app.get("/items/")
def read_items(q: str | None = None):
    return {"q": q}
```

[1][4]

**Fontes:**
- [1] FastAPI — Query Parameters › Query Parameters › Optional parameters (distância 0.1055, nota 10.72)
- [4] FastAPI — Query Parameters › Query Parameters (distância 0.1316, nota 6.43)

`modelo: groq:openai/gpt-oss-120b | tokens: 1113+230 | tentativas: 1 | 3257 ms`

## q37 — Como importar a aplicação no arquivo de testes quando ele fica no mesmo pacote do main.py?

*Tipo: procedimento · deve responder · referência: Com import relativo, por exemplo from .main import app.*

Use um import relativo para trazer o objeto `app` do módulo `main.py`:

```python
from .main import app
```

[1]

**Fontes:**
- [1] FastAPI — Testing › Testing › Separating tests › Testing file (distância 0.1121, nota 10.11)

`modelo: groq:openai/gpt-oss-120b | tokens: 1462+273 | tentativas: 1 | 4185 ms`

## q38 — Como criar uma rede no compose sem acesso externo, para isolar um banco de dados?

*Tipo: procedimento · deve responder · referência: Declarando a rede com internal: true.*

Para isolar um banco de dados crie uma rede interna no `docker‑compose.yml` definindo a opção `internal: true`. Essa rede não tem gateway externo, portanto os containers conectados a ela não conseguem acesso fora da rede do Compose.

```yaml
services:
  db:
    image: postgres
    networks:
      - isolated      # conecta o banco à rede interna

networks:
  isolated:
    internal: true   # sem conectividade externa
```

Somente os serviços que precisam acessar o banco devem ser ligados à rede `isolated`; se um serviço estiver conectado também a uma rede não‑interna, ele ainda poderá alcançar a internet por essa outra rede [1].

**Fontes:**
- [1] Docker Compose — Networking › Specify custom networks › Internal networks (distância 0.1606, nota 5.52)

`modelo: groq:openai/gpt-oss-120b | tokens: 1296+304 | tentativas: 1 | 2892 ms`

## q39 — Como fazer serviços de dois projetos compose diferentes conversarem entre si?

*Tipo: procedimento · deve responder · referência: Criando uma rede compartilhada uma vez e referenciando-a como external nos dois projetos.*

Crie uma rede externa compartilhada e referencie‑a em ambos os projetos:

1. Crie a rede uma única vez:  
   ```bash
   docker network create inter-project
   ```  
   [1]

2. Nos arquivos `docker‑compose.yaml` de cada projeto, declare a rede como externa e associe os serviços a ela:  

   ```yaml
   networks:
     shared:
       external: true
       name: inter-project
   ```

   ```yaml
   services:
     api:          # ou web, etc.
       networks:
         - shared
   ```  
   [1]

3. Os serviços conectados à mesma rede externa podem se comunicar usando o nome do serviço, como se estivessem no mesmo projeto:  
   `http://api:8080` por exemplo.  
   [1][2]

**Importante:** a rede externa deve existir antes de executar `docker compose up`; caso contrário, o Compose falha com “Network not found”.  
[2]

**Fontes:**
- [1] Docker Compose — Networking › Use an existing external network › Connecting multiple Compose projects (distância 0.1889, nota 6.53)
- [2] Docker Compose — Networking › Use an existing external network › Connecting multiple Compose projects (distância 0.2015, nota 4.81)

`modelo: groq:openai/gpt-oss-120b | tokens: 1296+375 | tentativas: 1 | 3010 ms`

## q40 — Como carregar as variáveis de ambiente de um serviço a partir de um arquivo no compose?

*Tipo: procedimento · deve responder · referência: Com o atributo env_file apontando para um arquivo .env.*

Use o atributo `env_file` no serviço do `compose.yaml` apontando para o(s) arquivo(s) `.env` que contêm as variáveis.  

```yaml
services:
  webapp:
    env_file: "webapp.env"
```

O `env_file` permite carregar variáveis a partir de um ou mais arquivos `.env` e os caminhos são relativos ao local do `compose.yaml` [3][5].

**Fontes:**
- [3] Docker Compose — Set environment variables › Use the `env_file` attribute (distância 0.1584, nota 6.15)
- [5] Docker Compose — Set environment variables › Use the `env_file` attribute (distância 0.1621, nota 4.84)

`modelo: groq:openai/gpt-oss-120b | tokens: 1028+236 | tentativas: 1 | 2599 ms`

## q41 — Como criar um índice em uma coluna de uma tabela no PostgreSQL?

*Tipo: procedimento · deve responder · referência: Com CREATE INDEX nome ON tabela (coluna).*

Para criar um índice basta usar o comando `CREATE INDEX`, especificando o nome do índice, a tabela e a coluna que será indexada. Por exemplo:

```sql
CREATE INDEX test1_id_index ON test1 (id);
```

O nome do índice (`test1_id_index` no exemplo) pode ser escolhido livremente, de modo que facilite a identificação posterior do seu propósito [2].

**Fontes:**
- [2] PostgreSQL 16 — Indexes: Introduction › 11.1. Introduction # (distância 0.1476, nota 6.67)

`modelo: groq:openai/gpt-oss-120b | tokens: 1457+211 | tentativas: 1 | 2610 ms`

## q42 — Como passar um servidor Redis que usa snapshots RDB para AOF sem perder dados?

*Tipo: procedimento · deve responder · referência: Habilitando o AOF com CONFIG SET no servidor em execução antes de alterar o arquivo de configuração.*

Sim. Para converter um servidor Redis que usa snapshots RDB para AOF sem perder dados, você deve habilitar o AOF via comando `CONFIG` no servidor em execução, seguindo o procedimento abaixo para Redis >= 2.2 [1].

**Preparação:**
*   Faça um backup do seu arquivo `dump.rdb` mais recente.
*   Transfira este backup para um local seguro [1].

**Mudança para AOF no banco de dados em execução:**
*   Habilite o AOF: `redis-cli config set appendonly yes` [2].
*   Opcionalmente, desative o RDB: `redis-cli config set save ""` [2].
*   Verifique se as gravações estão sendo adicionadas corretamente ao arquivo append-only [2].
*   **IMPORTANTE:** Atualize seu `redis.conf` (possivelmente através de `CONFIG REWRITE`) e certifique-se de que ele corresponda à configuração acima [2]. Se você esquecer esta etapa, ao reiniciar o servidor, as alterações de configuração serão perdidas e o servidor iniciará novamente com a configuração antiga, resultando em perda de dados [2].

**Na próxima reinicialização do servidor:**
*   Antes de reiniciar, aguarde a reescrita do AOF terminar de persistir os dados [4].
*   Você pode fazer isso observando `INFO persistence`, aguardando `aof_rewrite_in_progress` e `aof_rewrite_scheduled` serem `0`, e validando que `aof_last_bgrewrite_status` é `ok` [4].
*   Após reiniciar o servidor, verifique se o seu banco de dados contém o mesmo número de chaves que continha anteriormente [4].

**Nota:** Não seguir este procedimento (por exemplo, apenas alterando a configuração e reiniciando o servidor) pode resultar em perda de dados [1].

**Fontes:**
- [1] Redis — Persistence › Append-only file › How I can switch to AOF, if I'm currently using dump.rdb snapshots? (distância 0.1071, nota 10.85)
- [2] Redis — Persistence › Append-only file › How I can switch to AOF, if I'm currently using dump.rdb snapshots? (distância 0.1111, nota 10.55)
- [4] Redis — Persistence › Append-only file › How I can switch to AOF, if I'm currently using dump.rdb snapshots? (distância 0.1159, nota 8.65)

`modelo: groq:qwen/qwen3.8-27b | tokens: 1182+407 | tentativas: 1 | 8115 ms`

## q43 — Tenho as rotas /users/me e /users/{user_id} no FastAPI. Em que ordem devo declará-las?

*Tipo: procedimento · deve responder · referência: /users/me antes de /users/{user_id}, porque as rotas são avaliadas em ordem.*

Você deve declarar a rota `/users/me` antes da rota `/users/{user_id}` para que o FastAPI a reconheça corretamente e não a interprete como um parâmetro `user_id` com valor `"me"` [1].

**Fontes:**
- [1] FastAPI — Path Parameters › Path Parameters › Order matters (distância 0.1192, nota 6.14)

`modelo: groq:openai/gpt-oss-120b | tokens: 1221+150 | tentativas: 1 | 3709 ms`

## q44 — O que faz a opção XX do comando EXPIRE do Redis?

*Tipo: termo_exato · deve responder · referência: Só define a expiração se a chave já tiver uma.*

Define a expiração apenas quando a chave já possui um tempo de vida associado (TTL) [1].

**Fontes:**
- [1] Redis — EXPIRE (distância 0.1597, nota 5.76)

`modelo: groq:openai/gpt-oss-120b | tokens: 1335+127 | tentativas: 1 | 2622 ms`

## q45 — O que faz a opção GT do comando EXPIRE do Redis?

*Tipo: termo_exato · deve responder · referência: Só define a expiração se a nova for maior que a atual.*

A opção **GT** faz com que o `EXPIRE` só defina o tempo de vida quando o novo valor de expiração for **maior** que o já existente; chaves sem expiração são tratadas como tendo TTL infinito para essa comparação [1].

**Fontes:**
- [1] Redis — EXPIRE (distância 0.1491, nota 5.05)

`modelo: groq:openai/gpt-oss-120b | tokens: 1142+170 | tentativas: 1 | 3358 ms`

## q46 — Para que serve o sufixo :path em um parâmetro de rota do FastAPI?

*Tipo: termo_exato · deve responder · referência: Faz o parâmetro aceitar um caminho inteiro, incluindo barras.*

O sufixo `:path` indica que o parâmetro deve capturar **qualquer caminho**, incluindo barras (`/`). Assim, o parâmetro aceita valores como `/home/johndoe/myfile.txt`, permitindo que a rota receba um caminho completo em vez de um único segmento [2].

**Fontes:**
- [2] FastAPI — Path Parameters › Path Parameters › Path parameters containing paths › Path convertor (distância 0.1484, nota 3.57)

`modelo: groq:openai/gpt-oss-120b | tokens: 1216+254 | tentativas: 1 | 3560 ms`

## q47 — O que significa condition: service_healthy no depends_on do compose?

*Tipo: termo_exato · deve responder · referência: O compose espera o healthcheck da dependência passar antes de criar o serviço.*

`condition: service_healthy` indica que o serviço dependente só será iniciado depois que a dependência marcada atingir o estado **healthy**, ou seja, passar no seu `healthcheck` definido. O Compose aguarda o término bem‑sucedido do healthcheck da dependência antes de criar o serviço que a referencia [1][2][3].

**Fontes:**
- [1] Docker Compose — Control startup and shutdown order › Example (distância 0.1438, nota 4.55)
- [2] Docker Compose — Control startup and shutdown order › Control startup (distância 0.1586, nota 4.22)
- [3] Docker Compose — Control startup and shutdown order › Example (distância 0.1562, nota -0.5)

`modelo: groq:openai/gpt-oss-120b | tokens: 1263+337 | tentativas: 1 | 2902 ms`

## q48 — O que significa appendfsync everysec no Redis?

*Tipo: termo_exato · deve responder · referência: fsync a cada segundo: rápido, com risco de perder até 1 segundo de dados.*

`appendfsync everysec` indica que o Redis executa `fsync` no arquivo AOF a cada segundo. Essa política oferece boa velocidade (próxima ao snapshot) e, em caso de falha, pode perder até um segundo de dados [1][2].

**Fontes:**
- [1] Redis — Persistence › Append-only file › How durable is the append only file? (distância 0.1108, nota 9.73)
- [2] Redis — Persistence › Append-only file › How durable is the append only file? (distância 0.1204, nota 4.71)

`modelo: groq:openai/gpt-oss-120b | tokens: 1173+262 | tentativas: 1 | 2699 ms`

## q49 — Qual código de saída o pg_isready retorna quando o servidor está rejeitando conexões?

*Tipo: termo_exato · deve responder · referência: 1 (por exemplo, durante a inicialização).*

1 [1]

**Fontes:**
- [1] PostgreSQL 16 — pg_isready › Exit Status (distância 0.1151, nota 7.01)

`modelo: groq:openai/gpt-oss-120b | tokens: 1085+134 | tentativas: 1 | 2698 ms`

## q50 — O que é o HyperLogLog no Redis?

*Tipo: termo_exato · deve responder · referência: Estrutura que estima de forma probabilística a cardinalidade de conjuntos grandes.*

O HyperLogLog é uma estrutura de dados do Redis que fornece estimativas probabilísticas da cardinalidade (ou seja, do número de elementos) de conjuntos muito grandes[1]. Ele faz parte dos tipos de dados probabilísticos disponíveis no Redis[4].

**Fontes:**
- [1] Redis — Data types › Data types › HyperLogLog (distância 0.126, nota 9.81)
- [4] Redis — Data types › Data types (distância 0.1493, nota 0.46)

`modelo: groq:openai/gpt-oss-120b | tokens: 1184+208 | tentativas: 1 | 2697 ms`

## q51 — Defini uma expiração com EXPIRE no Redis. Como confiro quantos segundos ainda faltam para a chave sumir?

*Tipo: dois_docs · deve responder · referência: EXPIRE recebe o tempo em segundos; o comando TTL retorna o tempo restante.*

Não encontrei essa informação nos documentos carregados.

> Aviso: O modelo indicou que os trechos não respondem à pergunta.

**Trechos mais próximos:**
- [1] Redis — EXPIRE › Details › Appendix: Redis expires (distância 0.1389, nota 3.85)
- [2] Redis — EXPIRE › Details › Appendix: Redis expires (distância 0.1324, nota 3.41)
- [3] Redis — EXPIRE (distância 0.1382, nota 2.89)

`modelo: groq:openai/gpt-oss-120b | tokens: 1436+155 | tentativas: 1 | 2435 ms`

## q52 — Numa mesma função do FastAPI, como o framework sabe se um parâmetro vem do caminho, da query ou do corpo?

*Tipo: dois_docs · deve responder · referência: Os que estão no caminho são de rota; tipos simples fora do caminho são query; modelos Pydantic vêm do corpo.*

FastAPI analisa a assinatura da função:

* Se o nome do parâmetro também está definido na rota, ele é tratado como **parâmetro de caminho**.  
* Se o tipo do parâmetro é singular (`int`, `float`, `str`, `bool`, etc.), ele é interpretado como **parâmetro de query**.  
* Se o parâmetro é declarado como um modelo Pydantic, ele é interpretado como **corpo da requisição**.  

Além disso, quando o parâmetro tem valor padrão `= None`, FastAPI entende que ele não é obrigatório, independentemente da anotação de tipo `str | None` [1].

**Fontes:**
- [1] FastAPI — Request Body › Request Body › Request body + path + query parameters (distância 0.1503, nota 7.03)

`modelo: groq:openai/gpt-oss-120b | tokens: 1224+334 | tentativas: 1 | 2990 ms`

## q53 — No compose, o que é um serviço e como um serviço encontra outro na rede?

*Tipo: dois_docs · deve responder · referência: Serviço é um componente da aplicação (container com sua configuração); outros serviços o encontram pelo nome na rede padrão.*

Um **serviço** no Docker Compose é o componente computacional da aplicação definido no arquivo `compose.yaml`; ele representa um conceito abstrato que, na prática, é implementado executando uma ou mais vezes a mesma imagem de contêiner com sua configuração [4].

Um serviço **encontra** outro na rede através do DNS interno que o Compose cria para a rede padrão: ao iniciar, cada contêiner registra seu nome de serviço e pode ser resolvido pelos demais contêineres usando esse nome, sem necessidade de IPs ou configuração manual [2]. Links adicionais são opcionais, pois, por padrão, qualquer serviço pode alcançar outro pelo seu nome de serviço [1].

**Fontes:**
- [1] Docker Compose — Networking › Link containers (distância 0.1913, nota 2.52)
- [2] Docker Compose — Networking › Default network and service discovery (distância 0.1756, nota 2.5)
- [4] Docker Compose — How Compose works (distância 0.1782, nota 1.26)

`modelo: groq:openai/gpt-oss-120b | tokens: 1202+377 | tentativas: 1 | 6689 ms`

## q54 — Como habilitar CORS em uma API FastAPI?

*Tipo: sem_resposta · NÃO deve responder · referência: Não está nos documentos carregados.*

Não encontrei essa informação nos documentos carregados.

> Aviso: Trechos mais próximos, abaixo do limiar de relevância.

**Trechos mais próximos:**
- [1] FastAPI — First Steps › First Steps › Deploy your app (optional) (distância 0.1549, nota 0.3)
- [2] FastAPI — Dependencies › Dependencies › First Steps › Declare the dependency, in the "dependant" (distância 0.1557, nota -0.22)
- [3] FastAPI — First Steps › First Steps › `fastapi dev` with path or with `--entrypoint` CLI option (distância 0.1571, nota -0.44)

`modelo: None | tokens: 0+0 | tentativas: 0 | 2519 ms`

## q55 — Como configurar replicação streaming entre dois servidores PostgreSQL?

*Tipo: sem_resposta · NÃO deve responder · referência: Não está nos documentos.*

Não encontrei essa informação nos documentos carregados.

> Aviso: Trechos mais próximos, abaixo do limiar de relevância.

**Trechos mais próximos:**
- [1] PostgreSQL 16 — pg_isready › Options (distância 0.1789, nota -1.62)
- [2] Docker Compose — Networking › Debugging (distância 0.1843, nota -2.04)
- [3] PostgreSQL 16 — pg_isready › Options (distância 0.1904, nota -2.54)

`modelo: None | tokens: 0+0 | tentativas: 0 | 1545 ms`

## q56 — Como limitar a memória e a CPU de um serviço no docker compose?

*Tipo: sem_resposta · NÃO deve responder · referência: Não está nos documentos.*

Não encontrei essa informação nos documentos carregados.

> Aviso: Trechos mais próximos, abaixo do limiar de relevância.

**Trechos mais próximos:**
- [1] Docker Compose — How Compose works (distância 0.1579, nota 1.47)
- [2] Docker Compose — How Compose works › CLI › Key commands (distância 0.1422, nota 1.23)
- [3] Docker Compose — Networking › Debugging (distância 0.1635, nota 0.11)

`modelo: None | tokens: 0+0 | tentativas: 0 | 1589 ms`

## q57 — Como receber upload de arquivos em uma rota FastAPI?

*Tipo: sem_resposta · NÃO deve responder · referência: Não está nos documentos carregados.*

Não encontrei essa informação nos documentos carregados.

> Aviso: Trechos mais próximos, abaixo do limiar de relevância.

**Trechos mais próximos:**
- [1] FastAPI — First Steps › First Steps › Recap, step by step › Step 4: define the path operation function (distância 0.154, nota 1.01)
- [2] FastAPI — First Steps › First Steps › `fastapi dev` with path or with `--entrypoint` CLI option (distância 0.1537, nota 0.75)
- [3] FastAPI — Dependencies › Dependencies › First Steps › Declare the dependency, in the "dependant" (distância 0.164, nota 0.25)

`modelo: None | tokens: 0+0 | tentativas: 0 | 2660 ms`

## q58 — Qual a diferença entre VACUUM e VACUUM FULL no PostgreSQL?

*Tipo: sem_resposta · NÃO deve responder · referência: Não está nos documentos.*

Não encontrei essa informação nos documentos carregados.

> Aviso: Trechos mais próximos, abaixo do limiar de relevância.

**Trechos mais próximos:**
- [1] PostgreSQL 16 — Character Types › 8.3. Character Types # (distância 0.1864, nota -0.51)
- [2] PostgreSQL 16 — Character Types › 8.3. Character Types # › Tip (distância 0.1829, nota -0.89)
- [3] PostgreSQL 16 — Character Types › 8.3. Character Types # (distância 0.1824, nota -1.71)

`modelo: None | tokens: 0+0 | tentativas: 0 | 1605 ms`

## q59 — Como enviar um e-mail em segundo plano depois de responder uma requisição no FastAPI?

*Tipo: sem_resposta · NÃO deve responder · referência: Não está nos documentos carregados.*

Não encontrei essa informação nos documentos carregados.

> Aviso: Trechos mais próximos, abaixo do limiar de relevância.

**Trechos mais próximos:**
- [1] FastAPI — Request Body › Request Body (distância 0.1628, nota 0.68)
- [2] FastAPI — First Steps › First Steps (distância 0.1606, nota -0.44)
- [3] FastAPI — Query Parameters › Query Parameters (distância 0.1624, nota -1.05)

`modelo: None | tokens: 0+0 | tentativas: 0 | 2612 ms`

## q60 — Como criar um usuário e conceder permissões com GRANT no PostgreSQL?

*Tipo: sem_resposta · NÃO deve responder · referência: Não está nos documentos.*

Não encontrei essa informação nos documentos carregados.

> Aviso: Trechos mais próximos, abaixo do limiar de relevância.

**Trechos mais próximos:**
- [1] FastAPI — Dependencies › Dependencies › Simple and Powerful (distância 0.184, nota -0.92)
- [2] PostgreSQL 16 — Indexes: Introduction › 11.1. Introduction # (distância 0.1946, nota -2.16)
- [3] PostgreSQL 16 — Indexes: Introduction › 11.1. Introduction # (distância 0.2035, nota -2.2)

`modelo: None | tokens: 0+0 | tentativas: 0 | 1622 ms`
