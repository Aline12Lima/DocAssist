# Respostas do golden set (2026-11-12)

## Resumo

- Respondidas: 14 de 20
- Respondeu quando devia e recusou quando devia: 17 de 20
- Modelos usados: {'groq:openai/gpt-oss-120b': 11, 'nenhum': 2, 'groq:qwen/qwen3.8-27b': 7}

## q01 — O que o comando TTL do Redis retorna para uma chave que existe mas não tem expiração?

*Tipo: factual · deve responder · referência: Retorna -1.*

**Resposta curta:** O comando `TTL` devolve `-1` para uma chave que existe mas não possui expiração.  

**Detalhes:**  
- O retorno `-1` indica que a chave está presente no dataset, porém não tem um tempo de vida associado [1][2].  
- Exemplo na prática: após sobrescrever a chave `mykey` sem definir expiração, `TTL mykey` retorna `(integer) -1` [3].

**Fontes:**
- [1] Redis — TTL (distância 0.1031)
- [2] Redis — TTL › Return information (distância 0.1317)
- [3] Redis — EXPIRE › Examples (distância 0.1407)

`modelo: groq:openai/gpt-oss-120b | tokens: 1029+259 | tentativas: 1 | 11931 ms`

## q02 — O docker compose espera o banco de dados ficar pronto antes de iniciar a API?

*Tipo: factual · deve responder · referência: Não. Ele só espera o container estar rodando; para esperar ficar pronto, é preciso usar condition: service_healthy com um healthcheck.*

Sim, o Docker Compose pode aguardar o banco ficar pronto antes de iniciar a API, desde que a dependência seja declarada com a condição **`service_healthy`**. Nesse caso ele só cria o serviço da API depois que o healthcheck do banco indica que ele está “healthy”【1】【3】.  

**Detalhes:**  
- Por padrão o Compose só espera que o contêiner esteja em estado *running*, não que esteja pronto para aceitar conexões【2】.  
- Para que ele espere o estado pronto, usa‑se o atributo `depends_on` com `condition: service_healthy` (ou `service_started`, etc.)【2】.  
- No exemplo do trecho [3], o serviço `web` depende de `db` com `condition: service_healthy`; o Compose aguarda o healthcheck (`pg_isready …`) passar antes de criar `web`【3】.

**Fontes:**
- [3] Docker Compose — Control startup and shutdown order › Example (distância 0.1501)

`modelo: groq:openai/gpt-oss-120b | tokens: 1197+541 | tentativas: 1 | 1662 ms`

## q03 — No FastAPI, como os parâmetros de query aparecem na URL?

*Tipo: factual · deve responder · referência: São pares chave-valor depois do ? na URL, separados por &.*

**Resposta curta:**  
Os parâmetros de query são adicionados à URL após o caractere `?`, como pares `chave=valor` separados por `&`.  

**Detalhes:**  
No FastAPI (e em geral), a parte da query da URL contém os pares de chave‑valor que vêm depois do `?` e são separados por `&`. Por exemplo:

```
http://127.0.0.1:8000/items/?skip=0&limit=10
```

Aqui `skip=0` e `limit=10` são parâmetros de query. [1][2]

**Fontes:**
- [1] FastAPI — Query Parameters › Query Parameters › Defaults (distância 0.1142)
- [2] FastAPI — Query Parameters › Query Parameters (distância 0.1161)

`modelo: groq:openai/gpt-oss-120b | tokens: 1303+355 | tentativas: 1 | 1345 ms`

## q04 — Como configurar um Ingress no Kubernetes?

*Tipo: sem_resposta · NÃO deve responder · referência: Não está nos documentos.*

Não encontrei essa informação nos documentos carregados.

> Aviso: Trechos mais próximos, abaixo do limiar de relevância.

**Trechos mais próximos:**
- [1] Docker Compose — Networking › Specify custom networks (distância 0.1825)
- [2] Docker Compose — Control startup and shutdown order › Reference information (distância 0.1842)
- [3] Docker Compose — Networking › Debugging (distância 0.186)

`modelo: None | tokens: 0+0 | tentativas: 0 | 16 ms`

## q05 — Qual a diferença entre a persistência RDB e a AOF no Redis?

*Tipo: factual · deve responder · referência: O RDB salva fotos (snapshots) dos dados em intervalos definidos; o AOF registra cada operação de escrita e a reexecuta quando o servidor reinicia.*

**Resposta curta:**  
RDB cria snapshots pontuais compactos do dataset, enquanto AOF registra sequencialmente cada operação de escrita recebida pelo servidor.  

**Detalhes:**  

- **RDB**  
  - Faz “point‑in‑time snapshots” do conjunto de dados em intervalos especificados [2].  
  - Gera um único arquivo compacto, ideal para backups e recuperação de desastres [5].  
  - O processo pai do Redis apenas faz fork; o filho realiza todo o I/O de disco, permitindo que o pai continue atendendo clientes [5].  
  - Proporciona reinicializações mais rápidas, especialmente com grandes volumes de dados [5].  

- **AOF**  
  - Loga **todas** as operações de escrita usando o próprio formato do protocolo Redis, permitindo reconstruir o dataset ao iniciar [2].  
  - Os arquivos AOF costumam ser maiores que os RDB equivalentes [4].  
  - Pode ser mais lento que RDB, dependendo da política de *fsync*; com *fsync* a cada segundo ainda tem bom desempenho, mas RDB oferece garantias de latência menores sob carga pesada [4].  
  - Durante a reescrita (rewrite) do AOF, as escritas são armazenadas em memória e depois gravadas no novo arquivo, consumindo memória adicional e escrevendo comandos duas vezes [4].  

- **Interação entre os dois**  
  - Quando ambos os métodos estão habilitados, ao reiniciar o Redis o arquivo AOF tem prioridade para reconstruir o dataset, pois é garantido ser o mais completo [1].  
  - O Redis evita que um rewrite de AOF e um snapshot RDB ocorram simultaneamente, prevenindo I/O pesado concorrente [1].

**Fontes:**
- [1] Redis — Persistence › Interactions between AOF and RDB persistence (distância 0.0975)
- [2] Redis — Persistence (distância 0.102)
- [4] Redis — Persistence › AOF disadvantages (distância 0.1051)
- [5] Redis — Persistence › RDB advantages (distância 0.1179)

`modelo: groq:openai/gpt-oss-120b | tokens: 2516+1046 | tentativas: 2 | 4321 ms`

## q06 — Como os containers de um mesmo projeto do compose se encontram na rede?

*Tipo: factual · deve responder · referência: Pelo nome do serviço: cada serviço registra o nome num DNS interno da rede padrão do projeto.*

Os containers de um mesmo projeto do Compose se conectam ao **mesmo network padrão** que o Compose cria (nome `<project‑name>_default`). Cada container entra nessa rede, registra seu **nome de serviço** em um DNS interno e, assim, pode ser localizado pelos demais containers usando apenas o nome (ex.: `web`, `db`).  

**Detalhes**

- Ao executar `docker compose up`, o Compose cria uma rede chamada `<project‑name>_default` e anexa todos os serviços a ela [2].  
- Cada container se junta a essa rede com o nome do serviço, permitindo que outros containers façam lookup desse nome e recebam o IP correspondente [4].  
- O DNS interno da rede resolve os nomes, de modo que não é necessário usar endereços IP nem configuração manual [2][4].

**Fontes:**
- [2] Docker Compose — Networking › Default network and service discovery (distância 0.1738)
- [4] Docker Compose — Networking › Default network and service discovery (distância 0.178)

`modelo: groq:openai/gpt-oss-120b | tokens: 1184+466 | tentativas: 1 | 1349 ms`

## q07 — Como o docker compose define o nome do projeto quando nenhum nome é informado?

*Tipo: factual · deve responder · referência: Usa o nome da pasta onde está o arquivo do compose.*

O Docker Compose usa, por padrão, o nome da pasta que contém o arquivo `compose.yaml` como nome do projeto quando nenhum nome é especificado [4].  

**Detalhes:**  
- Se nenhum nome for definido via flag `-p`, variável `COMPOSE_PROJECT_NAME` ou atributo `name:` no arquivo, o Compose recorre ao nome base do diretório onde o arquivo de composição está localizado (ou, se houver múltiplos arquivos, ao nome base do primeiro arquivo especificado) [2][4].

**Fontes:**
- [2] Docker Compose — Specify a project name › Set a project name (distância 0.1509)
- [4] Docker Compose — Specify a project name (distância 0.1593)

`modelo: groq:openai/gpt-oss-120b | tokens: 932+313 | tentativas: 1 | 1095 ms`

## q08 — No PostgreSQL, qual tipo de texto é mais rápido: char(n), varchar(n) ou text?

*Tipo: factual · deve responder · referência: Não há diferença relevante de desempenho; o char(n) costuma ser o mais lento por ocupar mais espaço.*

**Resposta curta:** Não há diferença de desempenho entre `char(n)`, `varchar(n)` e `text`; na prática `text` ou `varchar` costumam ser tão rápidos ou mais rápidos que `char(n)` [3].

**Detalhes:**  
- O PostgreSQL não apresenta ganho de performance ao usar `char(n)` em comparação com `varchar(n)` ou `text`.  
- O tipo `char(n)` pode ser ligeiramente mais lento devido ao custo extra de armazenamento em branco e à verificação do comprimento ao inserir valores limitados.  
- Por isso, nas situações comuns recomenda‑se usar `text` ou `character varying` em vez de `character` [3].

**Fontes:**
- [3] PostgreSQL 16 — Character Types › 8.3. Character Types # › Tip (distância 0.1232)

`modelo: groq:openai/gpt-oss-120b | tokens: 1100+398 | tentativas: 1 | 2623 ms`

## q09 — Como escrever testes automatizados para uma API feita com FastAPI?

*Tipo: procedimento · deve responder · referência: Criar um TestClient passando a aplicação, escrever funções com nome começando em test_ e usar assert com o pytest.*

**Resposta curta:**  
Instale `pytest` e `httpx`, crie arquivos de teste com funções cujo nome começa com `test_`, use `TestClient` (passando a aplicação FastAPI) para fazer requisições e escreva `assert`s para validar as respostas; execute os testes com `uv run pytest` [1][2][3].

**Detalhes:**  

1. **Instalação das dependências**  
   - Adicione `pytest` ao projeto e instale‑o:  
     ```console
     $ uv add pytest
     ```  
   - Adicione `httpx` (necessário para o `TestClient`):  
     ```console
     $ uv add httpx
     ```  
   ([1] e [3]).

2. **Criação dos testes**  
   - Importe o cliente:  
     ```python
     from fastapi.testclient import TestClient   # ou from starlette.testclient import TestClient
     ```  
     ([3] e [5]).  
   - Instancie‑o passando a aplicação FastAPI:  
     ```python
     client = TestClient(app)
     ```  
   - Defina funções de teste com nome iniciando em `test_` (convenção padrão do `pytest`):  
     ```python
     def test_hello():
         response = client.get("/hello")
         assert response.status_code == 200
         assert response.json() == {"msg": "Hello"}
     ```  
     As funções são `def` normais, sem `async`, e as chamadas ao cliente são síncronas ([3]).

3. **Uso do cliente para diferentes tipos de dados**  
   - Passar parâmetros de caminho ou query: inclua‑os na URL.  
   - Enviar corpo JSON: `client.post("/items", json={"name": "foo"})`.  
   - Enviar form data: `client.post("/login", data={"username": "a", "password": "b"})`.  
   - Enviar cabeçalhos: `client.get("/protected", headers={"Authorization": "Bearer …"})`.

**Fontes:**
- [1] FastAPI — Testing › Testing › Run it (distância 0.1245)
- [2] FastAPI — Testing › Testing (distância 0.1298)
- [3] FastAPI — Testing › Testing › Using `TestClient` (distância 0.131)
- [5] FastAPI — Testing › Testing › Using `TestClient` (distância 0.1342)

`modelo: groq:openai/gpt-oss-120b | tokens: 1064+800 | tentativas: 1 | 2171 ms`

## q10 — Como recebo dados em JSON no corpo de uma requisição no FastAPI?

*Tipo: procedimento · deve responder · referência: Declarando um modelo Pydantic (classe que herda de BaseModel) e usando-o como tipo de um parâmetro da função.*

Para receber dados em JSON no corpo de uma requisição no FastAPI, você deve declarar um parâmetro na função da operação de caminho com o tipo definido como um modelo Pydantic (que herda de `BaseModel`) [1].

Detalhes do processo:

1.  **Importar e Criar o Modelo**: Importe `BaseModel` do `pydantic` e crie uma classe que herde dele, definindo os atributos com tipos Python padrão [5].
2.  **Declarar o Parâmetro**: Na função da operação de caminho, declare o parâmetro com o tipo do modelo criado (ex: `Item`) [1].
3.  **Processamento Automático**: Ao fazer isso, o FastAPI:
    *   Lê o corpo da requisição como JSON [1].
    *   Converte os tipos correspondentes, se necessário [1].
    *   Valida os dados [1].
    *   Retorna um erro claro se os dados forem inválidos [1].
    *   Fornece os dados recebidos no parâmetro declarado [1].
    *   Gera definições de JSON Schema para o modelo, que serão incluídas no schema OpenAPI e na documentação automática [1][3].

**Regra de Identificação**: O FastAPI interpreta um parâmetro como corpo da requisição se ele for declarado com o tipo de um modelo Pydantic [2].

**Fontes:**
- [1] FastAPI — Request Body › Request Body (distância 0.1264)
- [2] FastAPI — Request Body › Request Body › Request body + path + query parameters (distância 0.1306)
- [3] FastAPI — Request Body › Request Body › Automatic docs (distância 0.1319)
- [5] FastAPI — Request Body › Request Body (distância 0.1346)

`modelo: groq:qwen/qwen3.8-27b | tokens: 1080+312 | tentativas: 1 | 1555 ms`

## q11 — Como definir variáveis de ambiente para um serviço no docker compose?

*Tipo: procedimento · deve responder · referência: Com o atributo environment no serviço (em lista ou mapa) ou com o atributo env_file apontando para um arquivo .env.*

**Resposta curta:**  
Defina as variáveis de ambiente no serviço usando o atributo `environment` no `compose.yaml`, podendo usar a sintaxe de mapeamento ou de lista.

**Detalhes:**  
- **Sintaxe de mapeamento:**  

```yaml
services:
  webapp:
    environment:
      DEBUG: "true"
```  

- **Sintaxe de lista (equivalente):**  

```yaml
services:
  webapp:
    environment:
      - DEBUG=true
```  

- É possível declarar a variável sem valor para que o Compose a copie do shell onde o comando é executado:  

```yaml
services:
  web:
    environment:
      - DEBUG
```  

- Também pode usar interpolação, recebendo o valor do shell ou de um arquivo `.env` e emitindo aviso se não estiver definido:  

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

`modelo: groq:openai/gpt-oss-120b | tokens: 830+311 | tentativas: 1 | 1157 ms`

## q12 — Como fazer uma chave do Redis ser apagada sozinha depois de um tempo?

*Tipo: procedimento · deve responder · referência: Usando o comando EXPIRE com a chave e o tempo em segundos.*

Não encontrei essa informação nos documentos carregados.

> Aviso: O modelo indicou que os trechos não respondem à pergunta.

**Trechos mais próximos:**
- [1] Redis — Persistence › Append-only file › How I can switch to AOF, if I'm currently using dump.rdb snapshots? (distância 0.1528)
- [2] Redis — Persistence › Append-only file › How I can switch to AOF, if I'm currently using dump.rdb snapshots? (distância 0.1588)
- [3] Redis — Persistence › Append-only file › How I can switch to AOF, if I'm currently using dump.rdb snapshots? (distância 0.159)

`modelo: groq:qwen/qwen3.8-27b | tokens: 1074+7 | tentativas: 1 | 718 ms`

## q13 — Como reaproveitar a mesma lógica, como a conexão com o banco, em várias rotas do FastAPI?

*Tipo: procedimento · deve responder · referência: Usando o sistema de injeção de dependências do FastAPI: uma função de dependência declarada com Depends nas rotas.*

Não encontrei essa informação nos documentos carregados.

> Aviso: O modelo indicou que os trechos não respondem à pergunta.

**Trechos mais próximos:**
- [1] FastAPI — Testing › Testing › Testing: extended example › Extended testing file (distância 0.1561)
- [2] FastAPI — First Steps › First Steps › Recap (distância 0.1578)
- [3] FastAPI — Path Parameters › Path Parameters › Predefined values › Working with Python *enumerations* (distância 0.1594)

`modelo: groq:qwen/qwen3.8-27b | tokens: 2608+392 | tentativas: 2 | 3533 ms`

## q14 — Para que serve o pg_isready?

*Tipo: termo_exato · deve responder · referência: Verifica se o servidor PostgreSQL está aceitando conexões; o código de saída indica o resultado.*

O `pg_isready` é uma utilidade para verificar o status de conexão de um servidor de banco de dados PostgreSQL [1]. O status de saída (exit status) especifica o resultado da verificação de conexão [1].

Detalhes:
*   Ele retorna `0` se o servidor estiver aceitando conexões normalmente, `1` se estiver rejeitando conexões (por exemplo, durante a inicialização), `2` se não houver resposta à tentativa de conexão e `3` se nenhuma tentativa foi feita (por exemplo, devido a parâmetros inválidos) [4].
*   Não é necessário fornecer valores corretos de nome de usuário, senha ou nome do banco de dados para obter o status do servidor; no entanto, se valores incorretos forem fornecidos, o servidor registrará uma tentativa de conexão falha [2].
*   Ele utiliza as variáveis de ambiente suportadas pela `libpq` [5].

**Fontes:**
- [1] PostgreSQL 16 — pg_isready (distância 0.1231)
- [2] PostgreSQL 16 — pg_isready (distância 0.136)
- [4] PostgreSQL 16 — pg_isready › Exit Status (distância 0.1417)
- [5] PostgreSQL 16 — pg_isready › Environment (distância 0.1419)

`modelo: groq:qwen/qwen3.8-27b | tokens: 1579+368 | tentativas: 2 | 1823 ms`

## q15 — O que faz a opção NX do comando EXPIRE do Redis?

*Tipo: termo_exato · deve responder · referência: Só define a expiração se a chave ainda não tiver uma.*

A resposta gerada não indicou as fontes, por isso não foi exibida. Veja abaixo os trechos encontrados.

> Aviso: O modelo respondeu duas vezes sem citar as fontes.

**Trechos mais próximos:**
- [1] Redis — EXPIRE › Examples (distância 0.1224)
- [2] Redis — EXPIRE › Details › Differences in Redis prior to 2.1.3 (distância 0.1466)
- [3] Redis — EXPIRE (distância 0.148)
- [4] Redis — EXPIRE › Details › Refreshing expires (distância 0.1507)
- [5] Redis — EXPIRE › Details › Appendix: Redis expires (distância 0.1521)

`modelo: groq:openai/gpt-oss-120b | tokens: 1848+424 | tentativas: 2 | 2377 ms`

## q16 — No compose, um serviço fala com outro pela HOST_PORT ou pela CONTAINER_PORT?

*Tipo: termo_exato · deve responder · referência: Pela CONTAINER_PORT. A porta do host só é usada para acessar o serviço de fora da rede.*

Pela `CONTAINER_PORT`.

A comunicação entre serviços na rede usa a `CONTAINER_PORT`. A `HOST_PORT` é utilizada apenas para acessar o serviço de fora da rede. [2]

**Fontes:**
- [2] Docker Compose — Networking › Default network and service discovery (distância 0.1615)

`modelo: groq:qwen/qwen3.8-27b | tokens: 1238+42 | tentativas: 1 | 932 ms`

## q17 — Como fazer a API esperar o Postgres estar pronto para conexões no docker compose?

*Tipo: dois_docs · deve responder · referência: Definir um healthcheck no serviço do Postgres com pg_isready e usar depends_on com condition: service_healthy na API.*

Para fazer a API esperar o Postgres estar pronto, utilize a opção `depends_on` com a condição `service_healthy` no serviço da API, definindo um `healthcheck` no serviço do Postgres [2].

Detalhes da configuração:

*   No serviço da API (ex: `web`), defina `depends_on` apontando para o serviço do banco de dados (`db`) com `condition: service_healthy` [2].
*   No serviço do Postgres (`db`), configure um `healthcheck` que execute o comando `pg_isready` para verificar a disponibilidade do banco [1][2].
*   O exemplo de comando para o healthcheck é `pg_isready -U $${POSTGRES_USER} -d $${POSTGRES_DB}` [2].
*   O `pg_isready` aceita as opções `-U` para especificar o usuário e `-d` para especificar o nome do banco de dados [3][4].
*   O Compose criará os serviços na ordem de dependência, esperando que o `db` esteja "healthy" antes de criar o serviço da API [1][2].
*   Você pode configurar parâmetros de tempo no healthcheck, como `interval` (intervalo entre tentativas), `retries` (número de tentativas), `start_period` e `timeout` [2].

**Fontes:**
- [1] Docker Compose — Control startup and shutdown order › Example (distância 0.147)
- [2] Docker Compose — Control startup and shutdown order › Example (distância 0.1487)
- [3] PostgreSQL 16 — pg_isready › Options (distância 0.1529)
- [4] PostgreSQL 16 — pg_isready › Options (distância 0.1533)

`modelo: groq:qwen/qwen3.8-27b | tokens: 2349+903 | tentativas: 2 | 4626 ms`

## q18 — Por que a rede criada pelo compose do projeto se chama docassist_default?

*Tipo: dois_docs · deve responder · referência: O nome do projeto vem da pasta (DocAssist, em minúsculas), e a rede padrão se chama <nome-do-projeto>_default.*

A rede se chama `docassist_default` porque o nome da rede padrão do Docker Compose é baseado no "project name" (nome do projeto), que por padrão é derivado do nome do diretório onde o arquivo de configuração reside [1][4].

Como o nome do diretório (ou o nome do projeto definido) é `docassist`, o Compose cria automaticamente uma rede com o padrão `<project-name>_default`, resultando em `docassist_default` [2][3].

**Fontes:**
- [1] Docker Compose — Networking › Default network and service discovery (distância 0.163)
- [2] Docker Compose — Networking › Default network and service discovery (distância 0.1666)
- [3] Docker Compose — Networking › Default network and service discovery (distância 0.1672)
- [4] Docker Compose — Specify a project name (distância 0.1701)

`modelo: groq:qwen/qwen3.8-27b | tokens: 1169+104 | tentativas: 1 | 941 ms`

## q19 — Como configurar autenticação com OAuth2 e tokens JWT no FastAPI?

*Tipo: sem_resposta · NÃO deve responder · referência: Não está nos documentos carregados.*

Não encontrei essa informação nos documentos carregados.

> Aviso: O modelo indicou que os trechos não respondem à pergunta.

**Trechos mais próximos:**
- [1] FastAPI — First Steps › First Steps › Deploy your app (optional) (distância 0.1559)
- [2] FastAPI — First Steps › First Steps (distância 0.161)
- [3] FastAPI — Request Body › Request Body (distância 0.1621)

`modelo: groq:openai/gpt-oss-120b | tokens: 1379+63 | tentativas: 1 | 529 ms`

## q20 — Como fazer backup de um banco MongoDB?

*Tipo: sem_resposta · NÃO deve responder · referência: Não está nos documentos.*

Não encontrei essa informação nos documentos carregados.

> Aviso: Trechos mais próximos, abaixo do limiar de relevância.

**Trechos mais próximos:**
- [1] Redis — Persistence › Backing up Redis data › Online backups with the BACKUP command family (distância 0.1715)
- [2] Redis — Persistence › Backing up Redis data (distância 0.1802)
- [3] Redis — Persistence › Backing up Redis data › Online backups with the BACKUP command family (distância 0.1851)

`modelo: None | tokens: 0+0 | tentativas: 0 | 71 ms`
