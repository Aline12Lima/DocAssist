# Respostas do golden set (2026-11-14)

## Resumo

- Prompt: answer_v2
- Respondidas: 16 de 20
- Respondeu quando devia e recusou quando devia: 19 de 20
- Precisou de 2ª tentativa (sem citação na 1ª): 0
- Latência com LLM: mediana 1250 ms, p95 18022 ms
- Modelos usados: {'groq:openai/gpt-oss-120b': 14, 'nenhum': 2, 'groq:qwen/qwen3.8-27b': 4}

## q01 — O que o comando TTL do Redis retorna para uma chave que existe mas não tem expiração?

*Tipo: factual · deve responder · referência: Retorna -1.*

Retorna `-1` quando a chave existe, mas não possui tempo de expiração associado [1][2].

**Fontes:**
- [1] Redis — TTL (distância 0.1031)
- [2] Redis — TTL › Return information (distância 0.1317)

`modelo: groq:openai/gpt-oss-120b | tokens: 1168+179 | tentativas: 1 | 18022 ms`

## q02 — O docker compose espera o banco de dados ficar pronto antes de iniciar a API?

*Tipo: factual · deve responder · referência: Não. Ele só espera o container estar rodando; para esperar ficar pronto, é preciso usar condition: service_healthy com um healthcheck.*

Sim. Quando o serviço da API (`web`) declara a dependência ao banco (`db`) com `condition: service_healthy` e o `db` possui um `healthcheck`, o Docker Compose aguarda o healthcheck passar (ou seja, que o banco esteja “healthy”) antes de criar o serviço da API [1][3].  

Sem essa condição, o Compose apenas espera o contêiner estar em execução, não necessariamente pronto [2].

**Fontes:**
- [1] Docker Compose — Control startup and shutdown order › Example (distância 0.1463)
- [2] Docker Compose — Control startup and shutdown order › Control startup (distância 0.1495)
- [3] Docker Compose — Control startup and shutdown order › Example (distância 0.1501)

`modelo: groq:openai/gpt-oss-120b | tokens: 1336+496 | tentativas: 1 | 1624 ms`

## q03 — No FastAPI, como os parâmetros de query aparecem na URL?

*Tipo: factual · deve responder · referência: São pares chave-valor depois do ? na URL, separados por &.*

No FastAPI, os parâmetros de query são incluídos na URL após o caractere `?`, como pares `chave=valor` separados por `&`. Por exemplo:

```
http://127.0.0.1:8000/items/?skip=0&limit=10
```

[2]

**Fontes:**
- [2] FastAPI — Query Parameters › Query Parameters (distância 0.1161)

`modelo: groq:openai/gpt-oss-120b | tokens: 1442+217 | tentativas: 1 | 1141 ms`

## q04 — Como configurar um Ingress no Kubernetes?

*Tipo: sem_resposta · NÃO deve responder · referência: Não está nos documentos.*

Não encontrei essa informação nos documentos carregados.

> Aviso: Trechos mais próximos, abaixo do limiar de relevância.

**Trechos mais próximos:**
- [1] Docker Compose — Networking › Specify custom networks (distância 0.1825)
- [2] Docker Compose — Control startup and shutdown order › Reference information (distância 0.1842)
- [3] Docker Compose — Networking › Debugging (distância 0.186)

`modelo: None | tokens: 0+0 | tentativas: 0 | 73 ms`

## q05 — Qual a diferença entre a persistência RDB e a AOF no Redis?

*Tipo: factual · deve responder · referência: O RDB salva fotos (snapshots) dos dados em intervalos definidos; o AOF registra cada operação de escrita e a reexecuta quando o servidor reinicia.*

RDB e AOF são os dois mecanismos de persistência oferecidos pelo Redis, e eles funcionam de forma diferente:

* **RDB** grava snapshots pontuais do dataset em intervalos configurados, gerando um único arquivo compacto. Esse arquivo é ideal para backups, restauração de versões antigas, transferência para outros data‑centers ou armazenamento em S3, e permite reinicializações mais rápidas, especialmente com grandes volumes de dados. O processo de persistência RDB é feito por um processo filho, de modo que o processo principal nunca realiza I/O de disco, o que maximiza a performance [5].

* **AOF** registra, em ordem, cada operação de escrita recebida pelo servidor, usando o mesmo formato do protocolo Redis. Na inicialização, o AOF pode ser reproduzido para reconstruir o dataset original. Os arquivos AOF costumam ser maiores que os RDB equivalentes e podem ser mais lentos, dependendo da política de *fsync*. Durante uma reescrita de AOF, as escritas são mantidas em memória e depois gravadas no novo arquivo, o que pode consumir memória adicional e fazer com que os comandos de escrita sejam gravados duas vezes no disco [4].

Além disso, é possível combinar os dois métodos (RDB + AOF) para obter os benefícios de ambos [2].

**Fontes:**
- [2] Redis — Persistence (distância 0.102)
- [4] Redis — Persistence › AOF disadvantages (distância 0.1051)
- [5] Redis — Persistence › RDB advantages (distância 0.1179)

`modelo: groq:openai/gpt-oss-120b | tokens: 1381+450 | tentativas: 1 | 1493 ms`

## q06 — Como os containers de um mesmo projeto do compose se encontram na rede?

*Tipo: factual · deve responder · referência: Pelo nome do serviço: cada serviço registra o nome num DNS interno da rede padrão do projeto.*

Os containers de um mesmo projeto do Compose são conectados ao **network padrão** criado por ele (nome `<nome‑do‑projeto>_default`) e podem se localizar usando o **nome do serviço** registrado no DNS interno da rede. Cada container se junta a essa rede `bridge` e, sem precisar de endereços IP fixos, resolve o nome do outro serviço para obter o IP correspondente.  

- O Compose cria automaticamente uma única rede `bridge` para o app e anexa todos os containers a ela, tornando‑os alcançáveis e descobríveis pelo nome do serviço [2].  
- Quando o container inicia, seu nome é registrado em um servidor DNS interno, permitindo que outros containers façam lookup do nome e recebam o IP correto [4].

**Fontes:**
- [2] Docker Compose — Networking › Default network and service discovery (distância 0.1738)
- [4] Docker Compose — Networking › Default network and service discovery (distância 0.178)

`modelo: groq:openai/gpt-oss-120b | tokens: 1323+410 | tentativas: 1 | 1250 ms`

## q07 — Como o docker compose define o nome do projeto quando nenhum nome é informado?

*Tipo: factual · deve responder · referência: Usa o nome da pasta onde está o arquivo do compose.*

Ele usa o nome do diretório que contém o `compose.yaml` como nome do projeto, ou seja, o nome base do diretório do projeto (ou, se houver múltiplos arquivos, o nome base do primeiro arquivo) [4][2].

**Fontes:**
- [2] Docker Compose — Specify a project name › Set a project name (distância 0.1509)
- [4] Docker Compose — Specify a project name (distância 0.1593)

`modelo: groq:openai/gpt-oss-120b | tokens: 1071+295 | tentativas: 1 | 1352 ms`

## q08 — No PostgreSQL, qual tipo de texto é mais rápido: char(n), varchar(n) ou text?

*Tipo: factual · deve responder · referência: Não há diferença relevante de desempenho; o char(n) costuma ser o mais lento por ocupar mais espaço.*

Não há diferença de desempenho entre os tipos `char(n)`, `varchar(n)` e `text`; na prática, `text` ou `varchar` são tão rápidos quanto, e `char(n)` pode ser até mais lento devido ao custo extra de armazenamento e verificação de comprimento [3].

**Fontes:**
- [3] PostgreSQL 16 — Character Types › 8.3. Character Types # › Tip (distância 0.1232)

`modelo: groq:openai/gpt-oss-120b | tokens: 1239+308 | tentativas: 1 | 1138 ms`

## q09 — Como escrever testes automatizados para uma API feita com FastAPI?

*Tipo: procedimento · deve responder · referência: Criar um TestClient passando a aplicação, escrever funções com nome começando em test_ e usar assert com o pytest.*

Instale o framework de testes `pytest` no projeto:

```console
$ uv add pytest
```[1]

Instale também o cliente HTTP `httpx`, que o `TestClient` usa internamente:

```console
$ uv add httpx
```[3]

Importe o `TestClient` (pode ser de `fastapi.testclient` ou de `starlette.testclient`) e crie‑o passando a aplicação FastAPI:

```python
from fastapi import FastAPI
from fastapi.testclient import TestClient  # ou: from starlette.testclient import TestClient

app = FastAPI()
client = TestClient(app)
```[3][5]

Escreva funções de teste cujo nome comece com `test_` (convenção padrão do `pytest`) usando chamadas síncronas ao cliente (não `await`):

```python
def test_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Hello World"}
```[3]

Nos testes você pode enviar dados da mesma forma que faria com `httpx`/`requests`:

* parâmetros de caminho ou query → incluídos na URL;
* corpo JSON → parâmetro `json` com um `dict`;
* dados de formulário → parâmetro `data`;
* cabeçalhos → parâmetro `headers` (dicionário);
* cookies → parâmetro `cookies` (dicionário).[4]

Execute os testes com:

```console
$ uv run pytest
```[1]

Esses passos permitem escrever e rodar testes automatizados para sua API FastAPI.

**Fontes:**
- [1] FastAPI — Testing › Testing › Run it (distância 0.1245)
- [3] FastAPI — Testing › Testing › Using `TestClient` (distância 0.131)
- [4] FastAPI — Testing › Testing › Testing: extended example › Extended testing file (distância 0.1335)
- [5] FastAPI — Testing › Testing › Using `TestClient` (distância 0.1342)

`modelo: groq:openai/gpt-oss-120b | tokens: 1203+600 | tentativas: 1 | 5620 ms`

## q10 — Como recebo dados em JSON no corpo de uma requisição no FastAPI?

*Tipo: procedimento · deve responder · referência: Declarando um modelo Pydantic (classe que herda de BaseModel) e usando-o como tipo de um parâmetro da função.*

Crie um modelo Pydantic (herdando de `BaseModel`) e, na sua *path operation*, declare um parâmetro desse modelo.  
Com isso o FastAPI :

* lê o corpo da requisição como JSON,
* converte e valida os tipos,
* devolve os dados já convertidos no parâmetro declarado.

```python
from pydantic import BaseModel

class Item(BaseModel):
    name: str
    description: str | None = None
    price: float
    tax: float | None = None

@app.post("/items/")
async def create_item(item: Item):
    # `item` contém os dados enviados no corpo JSON
    ...
```

[1][5]

**Fontes:**
- [1] FastAPI — Request Body › Request Body (distância 0.1264)
- [5] FastAPI — Request Body › Request Body (distância 0.1346)

`modelo: groq:openai/gpt-oss-120b | tokens: 1222+382 | tentativas: 1 | 1376 ms`

## q11 — Como definir variáveis de ambiente para um serviço no docker compose?

*Tipo: procedimento · deve responder · referência: Com o atributo environment no serviço (em lista ou mapa) ou com o atributo env_file apontando para um arquivo .env.*

Use o atributo `environment` dentro da definição do serviço no `compose.yaml`. Ele aceita duas sintaxes:

* **Mapeamento** (chave : valor):

```yaml
services:
  webapp:
    environment:
      DEBUG: "true"
```

* **Lista** (`‑ NOME=valor`):

```yaml
services:
  webapp:
    environment:
      - DEBUG=true
```

É possível omitir o valor para que o Compose copie o valor da variável presente no shell onde o comando é executado:

```yaml
services:
  web:
    environment:
      - DEBUG
```

ou usar interpolação, que gera um aviso se a variável não estiver definida:

```yaml
services:
  web:
    environment:
      - DEBUG=${DEBUG}
```

[2][5]

**Fontes:**
- [2] Docker Compose — Set environment variables › Use the `environment` attribute (distância 0.1319)
- [5] Docker Compose — Set environment variables › Use the `environment` attribute › Additional information (distância 0.1429)

`modelo: groq:openai/gpt-oss-120b | tokens: 969+559 | tentativas: 1 | 2123 ms`

## q12 — Como fazer uma chave do Redis ser apagada sozinha depois de um tempo?

*Tipo: procedimento · deve responder · referência: Usando o comando EXPIRE com a chave e o tempo em segundos.*

Não encontrei essa informação nos documentos carregados.

> Aviso: O modelo indicou que os trechos não respondem à pergunta.

**Trechos mais próximos:**
- [1] Redis — Persistence › Append-only file › How I can switch to AOF, if I'm currently using dump.rdb snapshots? (distância 0.1528)
- [2] Redis — Persistence › Append-only file › How I can switch to AOF, if I'm currently using dump.rdb snapshots? (distância 0.1588)
- [3] Redis — Persistence › Append-only file › How I can switch to AOF, if I'm currently using dump.rdb snapshots? (distância 0.159)

`modelo: groq:qwen/qwen3.8-27b | tokens: 1218+7 | tentativas: 1 | 780 ms`

## q13 — Como reaproveitar a mesma lógica, como a conexão com o banco, em várias rotas do FastAPI?

*Tipo: procedimento · deve responder · referência: Usando o sistema de injeção de dependências do FastAPI: uma função de dependência declarada com Depends nas rotas.*

Use o sistema de **Dependency Injection** do FastAPI. Crie uma função “dependable” que abra (ou recupere) a conexão com o banco e retorne‑a; essa função tem a mesma assinatura de uma *path operation* e pode ser injetada em qualquer rota usando `Depends` [4]. Assim a lógica de conexão fica centralizada e pode ser reutilizada em múltiplas rotas.

**Fontes:**
- [4] FastAPI — Dependencies › Dependencies › First Steps (distância 0.1609)

`modelo: groq:openai/gpt-oss-120b | tokens: 1412+259 | tentativas: 1 | 1141 ms`

## q14 — Para que serve o pg_isready?

*Tipo: termo_exato · deve responder · referência: Verifica se o servidor PostgreSQL está aceitando conexões; o código de saída indica o resultado.*

O `pg_isready` é uma utilidade para verificar o status da conexão de um servidor de banco de dados PostgreSQL [1]. Ele checa se o servidor está aceitando conexões e devolve um código de saída que indica o resultado da verificação [4].

**Fontes:**
- [1] PostgreSQL 16 — pg_isready (distância 0.1231)
- [4] PostgreSQL 16 — pg_isready › Exit Status (distância 0.1417)

`modelo: groq:openai/gpt-oss-120b | tokens: 924+192 | tentativas: 1 | 1142 ms`

## q15 — O que faz a opção NX do comando EXPIRE do Redis?

*Tipo: termo_exato · deve responder · referência: Só define a expiração se a chave ainda não tiver uma.*

A opção `NX` do comando `EXPIRE` define o tempo de expiração apenas quando a chave não possui uma expiração atual [3].

**Fontes:**
- [3] Redis — EXPIRE (distância 0.148)

`modelo: groq:qwen/qwen3.8-27b | tokens: 1044+34 | tentativas: 1 | 1147 ms`

## q16 — No compose, um serviço fala com outro pela HOST_PORT ou pela CONTAINER_PORT?

*Tipo: termo_exato · deve responder · referência: Pela CONTAINER_PORT. A porta do host só é usada para acessar o serviço de fora da rede.*

Usa a **CONTAINER_PORT** para comunicação entre serviços dentro da mesma rede do Compose; a **HOST_PORT** serve apenas para acesso ao serviço a partir de fora da rede. [2]

**Fontes:**
- [2] Docker Compose — Networking › Default network and service discovery (distância 0.1615)

`modelo: groq:openai/gpt-oss-120b | tokens: 1362+153 | tentativas: 1 | 935 ms`

## q17 — Como fazer a API esperar o Postgres estar pronto para conexões no docker compose?

*Tipo: dois_docs · deve responder · referência: Definir um healthcheck no serviço do Postgres com pg_isready e usar depends_on com condition: service_healthy na API.*

Sim. Para fazer a API (serviço `web`) esperar o Postgres (`db`) estar pronto, utilize a opção `depends_on` com a condição `service_healthy` e defina um `healthcheck` no serviço do Postgres [1][2].

O `healthcheck` deve usar o comando `pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB}` para verificar se o banco está pronto [1]. O exemplo de configuração no `docker-compose` é:

```yaml
services:
  web:
    build: .
    depends_on:
      db:
        condition: service_healthy
        restart: true
      redis:
        condition: service_started
  redis:
    image: redis
  db:
    image: postgres:18
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U $${POSTGRES_USER} -d $${POSTGRES_DB}"]
      interval: 10s
      retries: 5
      start_period: 30s
      timeout: 10s
```

Neste cenário, o Compose cria os serviços em ordem de dependência, esperando que o `db` esteja "healthy" antes de criar o `web` [1][2]. A opção `restart: true` garante que, se o `db` for reiniciado, o `web` também seja reiniciado para reestabelecer as conexões [1].

**Fontes:**
- [1] Docker Compose — Control startup and shutdown order › Example (distância 0.147)
- [2] Docker Compose — Control startup and shutdown order › Example (distância 0.1487)

`modelo: groq:qwen/qwen3.8-27b | tokens: 1299+321 | tentativas: 1 | 1556 ms`

## q18 — Por que a rede criada pelo compose do projeto se chama docassist_default?

*Tipo: dois_docs · deve responder · referência: O nome do projeto vem da pasta (DocAssist, em minúsculas), e a rede padrão se chama <nome-do-projeto>_default.*

A rede padrão criada pelo Compose recebe o nome `<nome‑do‑projeto>_default`. O nome do projeto, por padrão, é obtido a partir do nome do diretório onde está o `compose.yaml`; assim, se o diretório se chama **docassist**, a rede será **docassist_default** [1][2].

**Fontes:**
- [1] Docker Compose — Networking › Default network and service discovery (distância 0.163)
- [2] Docker Compose — Networking › Default network and service discovery (distância 0.1666)

`modelo: groq:openai/gpt-oss-120b | tokens: 1298+228 | tentativas: 1 | 1044 ms`

## q19 — Como configurar autenticação com OAuth2 e tokens JWT no FastAPI?

*Tipo: sem_resposta · NÃO deve responder · referência: Não está nos documentos carregados.*

Não encontrei essa informação nos documentos carregados.

> Aviso: O modelo indicou que os trechos não respondem à pergunta.

**Trechos mais próximos:**
- [1] FastAPI — First Steps › First Steps › Deploy your app (optional) (distância 0.1559)
- [2] FastAPI — First Steps › First Steps (distância 0.161)
- [3] FastAPI — Request Body › Request Body (distância 0.1621)

`modelo: groq:qwen/qwen3.8-27b | tokens: 1549+7 | tentativas: 1 | 626 ms`

## q20 — Como fazer backup de um banco MongoDB?

*Tipo: sem_resposta · NÃO deve responder · referência: Não está nos documentos.*

Não encontrei essa informação nos documentos carregados.

> Aviso: Trechos mais próximos, abaixo do limiar de relevância.

**Trechos mais próximos:**
- [1] Redis — Persistence › Backing up Redis data › Online backups with the BACKUP command family (distância 0.1715)
- [2] Redis — Persistence › Backing up Redis data (distância 0.1802)
- [3] Redis — Persistence › Backing up Redis data › Online backups with the BACKUP command family (distância 0.1851)

`modelo: None | tokens: 0+0 | tentativas: 0 | 28 ms`
