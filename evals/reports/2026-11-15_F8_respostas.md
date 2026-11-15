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
- Latência com LLM: mediana 3453 ms, p95 7805 ms
- Latência de todas as perguntas: mediana 3160 ms, p95 7805 ms
- Modelos usados: {'groq:openai/gpt-oss-120b': 45, 'nenhum': 12, 'groq:qwen/qwen3.8-27b': 3}

## q01 — O que o comando TTL do Redis retorna para uma chave que existe mas não tem expiração?

*Tipo: factual · deve responder · referência: Retorna -1.*

Retorna `-1` quando a chave existe, mas não possui tempo de expiração associado[1][2].

**Fontes:**
- [1] Redis — TTL (distância 0.1031, nota 10.82)
- [2] Redis — TTL › Return information (distância 0.1317, nota 9.92)

`modelo: groq:openai/gpt-oss-120b | tokens: 1284+153 | tentativas: 1 | 22275 ms`

## q02 — O docker compose espera o banco de dados ficar pronto antes de iniciar a API?

*Tipo: factual · deve responder · referência: Não. Ele só espera o container estar rodando; para esperar ficar pronto, é preciso usar condition: service_healthy com um healthcheck.*

Não. Por padrão o Docker Compose só aguarda que o contêiner esteja em execução, não que ele esteja pronto para receber conexões [1].

Para que o Compose espere o banco ficar “healthy” antes de iniciar a API, é necessário usar `depends_on` com a opção `condition: service_healthy` e definir um `healthcheck` no serviço do banco [4][1].

**Fontes:**
- [1] Docker Compose — Control startup and shutdown order › Control startup (distância 0.1495, nota 5.23)
- [4] Docker Compose — Control startup and shutdown order › Example (distância 0.1501, nota 0.74)

`modelo: groq:openai/gpt-oss-120b | tokens: 1271+434 | tentativas: 1 | 4388 ms`

## q03 — No FastAPI, como os parâmetros de query aparecem na URL?

*Tipo: factual · deve responder · referência: São pares chave-valor depois do ? na URL, separados por &.*

No FastAPI, os parâmetros de query são incluídos na URL após o caractere `?`, como pares `chave=valor` separados por `&`. Por exemplo:

```
http://127.0.0.1:8000/items/?skip=0&limit=10
```

[1]

**Fontes:**
- [1] FastAPI — Query Parameters › Query Parameters (distância 0.1161, nota 8.33)

`modelo: groq:openai/gpt-oss-120b | tokens: 1332+204 | tentativas: 1 | 2813 ms`

## q04 — Como configurar um Ingress no Kubernetes?

*Tipo: sem_resposta · NÃO deve responder · referência: Não está nos documentos.*

Não encontrei essa informação nos documentos carregados.

> Aviso: Trechos mais próximos, abaixo do limiar de relevância.

**Trechos mais próximos:**
- [1] Docker Compose — Networking › Default network and service discovery (distância 0.1964, nota -1.51)
- [2] Docker Compose — Networking › Debugging (distância 0.1913, nota -2.04)
- [3] Docker Compose — Control startup and shutdown order › Example (distância 0.1881, nota -3.28)

`modelo: None | tokens: 0+0 | tentativas: 0 | 1833 ms`

## q05 — Qual a diferença entre a persistência RDB e a AOF no Redis?

*Tipo: factual · deve responder · referência: O RDB salva fotos (snapshots) dos dados em intervalos definidos; o AOF registra cada operação de escrita e a reexecuta quando o servidor reinicia.*

RDB grava snapshots pontuais do dataset em intervalos definidos, gerando um único arquivo compacto que facilita backups, recuperação de desastres e reinicializações rápidas; já a AOF registra **cada** operação de escrita recebida, permitindo reconstruir o dataset reproduzindo o log, porém produz arquivos maiores, pode ser mais lenta e consome mais memória durante a reescrita.  

- RDB: “point‑in‑time snapshots” e “arquivo único e compacto”, ideal para backups e restaurações rápidas [1][4].  
- AOF: “logs every write operation” e “replay… reconstructing the original dataset” [1]; desvantagens incluem tamanho maior, possível lentidão e uso extra de memória durante rewrite [3].  
- Quando ambas estão habilitadas, no reinício o AOF tem prioridade para reconstruir o dataset [2].

**Fontes:**
- [1] Redis — Persistence (distância 0.102, nota 10.27)
- [2] Redis — Persistence › Interactions between AOF and RDB persistence (distância 0.0975, nota 10.25)
- [3] Redis — Persistence › AOF disadvantages (distância 0.1051, nota 8.98)
- [4] Redis — Persistence › RDB advantages (distância 0.1179, nota 7.81)

`modelo: groq:openai/gpt-oss-120b | tokens: 1381+507 | tentativas: 1 | 3403 ms`

## q06 — Como os containers de um mesmo projeto do compose se encontram na rede?

*Tipo: factual · deve responder · referência: Pelo nome do serviço: cada serviço registra o nome num DNS interno da rede padrão do projeto.*

Os containers de um mesmo projeto do Compose são conectados ao **mesmo network** (por padrão, o network `<project‑name>_default`). Cada container se junta a esse network, registra seu nome em um servidor DNS interno e, assim, pode ser alcançado pelos demais containers usando apenas o **nome do serviço** – sem precisar de endereços IP ou configuração manual [1].

**Fontes:**
- [1] Docker Compose — Networking › Default network and service discovery (distância 0.1738, nota 4.55)

`modelo: groq:openai/gpt-oss-120b | tokens: 1160+273 | tentativas: 1 | 2856 ms`

## q07 — Como o docker compose define o nome do projeto quando nenhum nome é informado?

*Tipo: factual · deve responder · referência: Usa o nome da pasta onde está o arquivo do compose.*

Por padrão o Docker Compose usa o nome do diretório que contém o `compose.yaml` como nome do projeto — ou seja, o nome base da pasta onde o arquivo está localizado [3][5].

**Fontes:**
- [3] Docker Compose — Specify a project name (distância 0.1593, nota 5.09)
- [5] Docker Compose — Networking › Default network and service discovery (distância 0.1705, nota 2.08)

`modelo: groq:openai/gpt-oss-120b | tokens: 1213+232 | tentativas: 1 | 2427 ms`

## q08 — No PostgreSQL, qual tipo de texto é mais rápido: char(n), varchar(n) ou text?

*Tipo: factual · deve responder · referência: Não há diferença relevante de desempenho; o char(n) costuma ser o mais lento por ocupar mais espaço.*

Não há diferença de desempenho relevante entre `char(n)`, `varchar(n)` e `text`; na prática `text` ou `varchar` são tão rápidos quanto, enquanto `char(n)` costuma ser o mais lento devido ao custo extra de armazenamento e ao preenchimento de espaços [1].

**Fontes:**
- [1] PostgreSQL 16 — Character Types › 8.3. Character Types # › Tip (distância 0.1232, nota 4.83)

`modelo: groq:openai/gpt-oss-120b | tokens: 1239+313 | tentativas: 1 | 3294 ms`

## q09 — Como escrever testes automatizados para uma API feita com FastAPI?

*Tipo: procedimento · deve responder · referência: Criar um TestClient passando a aplicação, escrever funções com nome começando em test_ e usar assert com o pytest.*

Para testar uma API FastAPI de forma automatizada, siga estes passos:

1. Instale as dependências de teste: `httpx` e `pytest` [1][2].
2. Crie um arquivo de testes (por exemplo, `test_main.py`) dentro do mesmo pacote da aplicação ou em outro módulo [3][5].
3. No arquivo de teste, importe a aplicação FastAPI e crie um `TestClient` passando‑a como argumento [1].
4. Escreva funções de teste cujo nome comece com `test_` (convenção do `pytest`) [1].
5. Dentro das funções, use o `TestClient` como usaria o `httpx` para fazer chamadas à API e escreva asserts com expressões Python padrão [1].
6. As funções de teste são `def` normais e as chamadas ao cliente não precisam de `await` [1].
7. Execute os testes com `uv run pytest`, que detectará e rodará automaticamente os arquivos de teste [2].

Exemplo resumido de estrutura de arquivos:

```
.
├── app
│   ├── __init__.py
│   ├── main.py          # contém a FastAPI app
│   └── test_main.py     # contém os testes
```

No `test_main.py` você pode importar a app com importação relativa e usar o `TestClient` conforme descrito acima [3].

**Fontes:**
- [1] FastAPI — Testing › Testing › Using `TestClient` (distância 0.131, nota 6.46)
- [2] FastAPI — Testing › Testing › Run it (distância 0.1245, nota 5.28)
- [3] FastAPI — Testing › Testing › Separating tests › Testing file (distância 0.1492, nota 4.86)
- [5] FastAPI — Testing › Testing › Separating tests (distância 0.1576, nota 3.35)

`modelo: groq:openai/gpt-oss-120b | tokens: 1224+677 | tentativas: 1 | 4711 ms`

## q10 — Como recebo dados em JSON no corpo de uma requisição no FastAPI?

*Tipo: procedimento · deve responder · referência: Declarando um modelo Pydantic (classe que herda de BaseModel) e usando-o como tipo de um parâmetro da função.*

Para receber dados JSON no corpo da requisição, declare um parâmetro do tipo de um modelo Pydantic na sua função de operação:

1. Importe `BaseModel` de **pydantic** e crie um modelo que herde dele, definindo os atributos com tipos Python padrão [2].
2. Na rota, adicione um parâmetro cujo tipo seja esse modelo; o FastAPI lerá o corpo da requisição como JSON, converterá os tipos, validará os dados e disponibilizará o objeto preenchido no parâmetro [1].

```python
from fastapi import FastAPI
from pydantic import BaseModel

class Item(BaseModel):
    name: str
    description: str | None = None
    price: float
    tax: float | None = None

app = FastAPI()

@app.post("/items/")
async def create_item(item: Item):
    # `item` contém os dados enviados no corpo JSON
    return item
```

* O FastAPI lê o corpo como JSON, converte tipos, valida e fornece os dados em `item` [1].  
* O modelo definido com `BaseModel` descreve a estrutura esperada do JSON [2].

**Fontes:**
- [1] FastAPI — Request Body › Request Body (distância 0.1264, nota 9.52)
- [2] FastAPI — Request Body › Request Body (distância 0.1346, nota 7.5)

`modelo: groq:openai/gpt-oss-120b | tokens: 1350+481 | tentativas: 1 | 4083 ms`

## q11 — Como definir variáveis de ambiente para um serviço no docker compose?

*Tipo: procedimento · deve responder · referência: Com o atributo environment no serviço (em lista ou mapa) ou com o atributo env_file apontando para um arquivo .env.*

Você pode definir variáveis de ambiente no `docker compose` de duas formas principais:

1. **Usando o atributo `environment` no `compose.yaml`** – basta acrescentar a chave `environment` dentro do serviço, usando sintaxe de mapeamento ou lista.  
   ```yaml
   services:
     webapp:
       environment:
         DEBUG: "true"
   ```  
   equivale a  
   ```yaml
   services:
     webapp:
       environment:
         - DEBUG=true
   ```  
   [1]

2. **Usando o atributo `env_file`** – aponta para um arquivo `.env` que contém as variáveis, permitindo reutilizá‑las em vários serviços ou com o comando `docker run --env-file`.  
   ```yaml
   services:
     webapp:
       env_file: "webapp.env"
   ```  
   [3]

> As variáveis de ambiente só são aplicadas quando há uma entrada explícita na configuração do serviço. [2]

**Fontes:**
- [1] Docker Compose — Set environment variables › Use the `environment` attribute (distância 0.1319, nota 10.13)
- [2] Docker Compose — Set environment variables (distância 0.139, nota 9.36)
- [3] Docker Compose — Set environment variables › Use the `env_file` attribute (distância 0.1524, nota 8.48)

`modelo: groq:openai/gpt-oss-120b | tokens: 999+533 | tentativas: 1 | 3453 ms`

## q12 — Como fazer uma chave do Redis ser apagada sozinha depois de um tempo?

*Tipo: procedimento · deve responder · referência: Usando o comando EXPIRE com a chave e o tempo em segundos.*

Use o comando da família **`EXPIRE`** (ou `PEXPIRE`) para associar um tempo de vida à chave.  
Depois que o tempo especificado expira, a chave é removida automaticamente pelo Redis — ela passa a ser considerada *volatile* [2][3].

**Fontes:**
- [2] Redis — EXPIRE › Details › Appendix: Redis expires (distância 0.1751, nota 3.23)
- [3] Redis — EXPIRE (distância 0.1721, nota 3.09)

`modelo: groq:openai/gpt-oss-120b | tokens: 1406+257 | tentativas: 1 | 3110 ms`

## q13 — Como reaproveitar a mesma lógica, como a conexão com o banco, em várias rotas do FastAPI?

*Tipo: procedimento · deve responder · referência: Usando o sistema de injeção de dependências do FastAPI: uma função de dependência declarada com Depends nas rotas.*

Não encontrei essa informação nos documentos carregados.

> Aviso: Trechos mais próximos, abaixo do limiar de relevância.

**Trechos mais próximos:**
- [1] FastAPI — Path Parameters › Path Parameters › Data validation (distância 0.1644, nota -0.78)
- [2] FastAPI — Dependencies › Dependencies › First Steps › Declare the dependency, in the "dependant" (distância 0.1663, nota -0.98)
- [3] FastAPI — Dependencies › Dependencies › First Steps (distância 0.1609, nota -1.27)

`modelo: None | tokens: 0+0 | tentativas: 0 | 2828 ms`

## q14 — Para que serve o pg_isready?

*Tipo: termo_exato · deve responder · referência: Verifica se o servidor PostgreSQL está aceitando conexões; o código de saída indica o resultado.*

O `pg_isready` é uma ferramenta que verifica o status de conexão de um servidor PostgreSQL, indicando se ele está aceitando conexões, rejeitando‑as ou não respondendo [1].

**Fontes:**
- [1] PostgreSQL 16 — pg_isready (distância 0.1231, nota 8.83)

`modelo: groq:openai/gpt-oss-120b | tokens: 1139+121 | tentativas: 1 | 6229 ms`

## q15 — O que faz a opção NX do comando EXPIRE do Redis?

*Tipo: termo_exato · deve responder · referência: Só define a expiração se a chave ainda não tiver uma.*

A opção `NX` define o expiração apenas quando a chave não possui expiração atual [1].

**Fontes:**
- [1] Redis — EXPIRE (distância 0.148, nota 5.76)

`modelo: groq:qwen/qwen3.8-27b | tokens: 1138+24 | tentativas: 1 | 7587 ms`

## q16 — No compose, um serviço fala com outro pela HOST_PORT ou pela CONTAINER_PORT?

*Tipo: termo_exato · deve responder · referência: Pela CONTAINER_PORT. A porta do host só é usada para acessar o serviço de fora da rede.*

Usa a **CONTAINER_PORT** para comunicação entre serviços; a **HOST_PORT** serve apenas para acesso externo ao contêiner [2].

**Fontes:**
- [2] Docker Compose — Networking › Default network and service discovery (distância 0.1615, nota 1.42)

`modelo: groq:openai/gpt-oss-120b | tokens: 1294+199 | tentativas: 1 | 2820 ms`

## q17 — Como fazer a API esperar o Postgres estar pronto para conexões no docker compose?

*Tipo: dois_docs · deve responder · referência: Definir um healthcheck no serviço do Postgres com pg_isready e usar depends_on com condition: service_healthy na API.*

Use o `depends_on` com a condição **`service_healthy`** e defina um *healthcheck* para o serviço Postgres que verifica a disponibilidade com `pg_isready`. Assim o contêiner da API só será criado depois que o Postgres for considerado “healthy”.

```yaml
services:
  api:
    build: .
    depends_on:
      db:
        condition: service_healthy   # aguarda o db ficar saudável
        restart: true                # opcional: reinicia a API se o db for reiniciado
  db:
    image: postgres:18
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U $${POSTGRES_USER} -d $${POSTGRES_DB}"]
      interval: 10s
      retries: 5
      start_period: 30s
      timeout: 10s
```

- O atributo `condition: service_healthy` faz a dependência aguardar o *healthcheck* do `db` antes de iniciar a API [1][3].  
- O *healthcheck* usa `pg_isready` para confirmar que o PostgreSQL está pronto para aceitar conexões [2][3].  

Com essa configuração, a API só iniciará quando o Postgres estiver pronto.

**Fontes:**
- [1] Docker Compose — Control startup and shutdown order › Control startup (distância 0.1588, nota 2.74)
- [2] Docker Compose — Control startup and shutdown order › Example (distância 0.147, nota 2.49)
- [3] Docker Compose — Control startup and shutdown order › Example (distância 0.1487, nota 1.32)

`modelo: groq:openai/gpt-oss-120b | tokens: 1256+440 | tentativas: 1 | 4308 ms`

## q18 — Por que a rede criada pelo compose do projeto se chama docassist_default?

*Tipo: dois_docs · deve responder · referência: O nome do projeto vem da pasta (DocAssist, em minúsculas), e a rede padrão se chama <nome-do-projeto>_default.*

Porque o Docker Compose cria automaticamente, ao executar `docker compose up`, uma rede padrão cujo nome é formado pelo nome do projeto seguido de `_default`. O nome do projeto costuma ser o nome do diretório (ou o valor definido com `-p`). Assim, para um projeto chamado **docassist**, a rede gerada será `docassist_default` [1][2].

**Fontes:**
- [1] Docker Compose — Networking › Default network and service discovery (distância 0.1666, nota 5.01)
- [2] Docker Compose — Networking › Default network and service discovery (distância 0.1672, nota 1.06)

`modelo: groq:openai/gpt-oss-120b | tokens: 1340+225 | tentativas: 1 | 2584 ms`

## q19 — Como configurar autenticação com OAuth2 e tokens JWT no FastAPI?

*Tipo: sem_resposta · NÃO deve responder · referência: Não está nos documentos carregados.*

Não encontrei essa informação nos documentos carregados.

> Aviso: Trechos mais próximos, abaixo do limiar de relevância.

**Trechos mais próximos:**
- [1] FastAPI — Request Body › Request Body (distância 0.1621, nota -0.43)
- [2] FastAPI — Path Parameters › Path Parameters › Predefined values › Working with Python *enumerations* (distância 0.1705, nota -0.66)
- [3] FastAPI — Request Body › Request Body › Request body + path + query parameters (distância 0.1751, nota -0.7)

`modelo: None | tokens: 0+0 | tentativas: 0 | 2537 ms`

## q20 — Como fazer backup de um banco MongoDB?

*Tipo: sem_resposta · NÃO deve responder · referência: Não está nos documentos.*

Não encontrei essa informação nos documentos carregados.

> Aviso: Trechos mais próximos, abaixo do limiar de relevância.

**Trechos mais próximos:**
- [1] Redis — Persistence › Backing up Redis data (distância 0.1802, nota -1.27)
- [2] Redis — Persistence › Backing up Redis data › Online backups with the BACKUP command family (distância 0.1715, nota -1.88)
- [3] Redis — Persistence › Disaster recovery (distância 0.1921, nota -1.99)

`modelo: None | tokens: 0+0 | tentativas: 0 | 1556 ms`

## q21 — O que o FastAPI gera automaticamente a partir das rotas usando o padrão OpenAPI?

*Tipo: factual · deve responder · referência: Um schema de toda a API no padrão OpenAPI, usado pela documentação automática.*

Ele gera automaticamente um **schema OpenAPI** (arquivo JSON) que descreve todas as rotas da aplicação, incluindo caminhos, parâmetros, respostas e demais detalhes da API [1][1]. Esse schema pode ser visualizado em `/openapi.json` e serve de base para as documentações interativas e para ferramentas compatíveis com OpenAPI [1][4].

**Fontes:**
- [1] FastAPI — First Steps › First Steps (distância 0.1371, nota 4.18)
- [4] FastAPI — Path Parameters › Path Parameters › Standards-based benefits, alternative documentation (distância 0.1408, nota 2.17)

`modelo: groq:openai/gpt-oss-120b | tokens: 1196+344 | tentativas: 1 | 4159 ms`

## q22 — A classe FastAPI herda de qual outra classe?

*Tipo: factual · deve responder · referência: De Starlette.*

A classe `FastAPI` herda diretamente da classe `Starlette` [1].

**Fontes:**
- [1] FastAPI — First Steps › First Steps › Recap, step by step › Step 1: import `FastAPI` (distância 0.1403, nota 4.23)

`modelo: groq:openai/gpt-oss-120b | tokens: 1110+115 | tentativas: 1 | 7421 ms`

## q23 — Se a rota declara item_id: int e eu acesso /items/3, a função recebe o valor como texto ou como inteiro?

*Tipo: factual · deve responder · referência: Como inteiro (int) do Python, não como string.*

Sim. A função recebe o valor como um inteiro (`int`), não como texto [string] [1]

**Fontes:**
- [1] FastAPI — Path Parameters › Path Parameters › Data conversion (distância 0.1627, nota 3.57)

`modelo: groq:openai/gpt-oss-120b | tokens: 1175+135 | tentativas: 1 | 3917 ms`

## q24 — Qual biblioteca faz a validação dos dados dos parâmetros por baixo dos panos no FastAPI?

*Tipo: factual · deve responder · referência: O Pydantic.*

Pydantic faz a validação dos dados dos parâmetros por baixo dos panos no FastAPI [1].

**Fontes:**
- [1] FastAPI — Path Parameters › Path Parameters › Pydantic (distância 0.1469, nota 4.32)

`modelo: groq:openai/gpt-oss-120b | tokens: 1283+122 | tentativas: 1 | 3676 ms`

## q25 — Qual é o nome padrão do arquivo de configuração do Docker Compose?

*Tipo: factual · deve responder · referência: compose.yaml (preferido) ou compose.yml, no diretório de trabalho.*

O nome padrão do arquivo de configuração do Docker Compose é `compose.yaml` (também aceita `compose.yml` como alternativa) [2].

**Fontes:**
- [2] Docker Compose — How Compose works › The Compose file (distância 0.1278, nota 6.04)

`modelo: groq:openai/gpt-oss-120b | tokens: 1237+184 | tentativas: 1 | 3041 ms`

## q26 — O que é um sorted set no Redis?

*Tipo: factual · deve responder · referência: Uma coleção de strings únicas ordenadas pelo score associado a cada uma.*

Um sorted set no Redis é uma coleção de strings únicas que mantêm a ordem com base em um score associado a cada string[1].

**Fontes:**
- [1] Redis — Data types › Data types (distância 0.108, nota 10.58)

`modelo: groq:openai/gpt-oss-120b | tokens: 1079+82 | tentativas: 1 | 6516 ms`

## q27 — Qual o custo de verificar se um elemento existe em um set do Redis?

*Tipo: factual · deve responder · referência: O(1): constante, independe do número de elementos.*

Não encontrei essa informação nos documentos carregados.

> Aviso: Trechos mais próximos, abaixo do limiar de relevância.

**Trechos mais próximos:**
- [1] Redis — Data types › Data types › Sets (distância 0.1386, nota -0.1)
- [2] Redis — Data types › Data types › Cuckoo filter (distância 0.1615, nota -0.14)
- [3] Redis — Data types › Data types (distância 0.1567, nota -0.98)

`modelo: None | tokens: 0+0 | tentativas: 0 | 1873 ms`

## q28 — No PostgreSQL, a tabela continua aceitando INSERT e UPDATE enquanto um índice está sendo criado?

*Tipo: factual · deve responder · referência: Por padrão não: leituras continuam, mas escritas ficam bloqueadas até o índice terminar.*

Não. Por padrão, o PostgreSQL bloqueia as operações de escrita (`INSERT`, `UPDATE`, `DELETE`) até que a criação do índice seja finalizada [2]. No entanto, é possível permitir que as escritas ocorram em paralelo com a criação do índice, embora existam ressalvas a serem consideradas [2].

**Fontes:**
- [2] PostgreSQL 16 — Indexes: Introduction › 11.1. Introduction # (distância 0.1402, nota 6.44)

`modelo: groq:qwen/qwen3.8-27b | tokens: 1433+66 | tentativas: 1 | 8425 ms`

## q29 — Qual é o tamanho máximo de uma string que o PostgreSQL consegue armazenar?

*Tipo: factual · deve responder · referência: Cerca de 1 GB.*

O PostgreSQL pode armazenar strings de até aproximadamente 1 GB de tamanho [1].

**Fontes:**
- [1] PostgreSQL 16 — Character Types › 8.3. Character Types # (distância 0.1246, nota 4.63)

`modelo: groq:openai/gpt-oss-120b | tokens: 1413+169 | tentativas: 1 | 3436 ms`

## q30 — No Redis, os arquivos AOF costumam ser maiores ou menores que os arquivos RDB?

*Tipo: factual · deve responder · referência: Maiores, para o mesmo conjunto de dados.*

Os arquivos AOF costumam ser maiores que os arquivos RDB equivalentes para o mesmo conjunto de dados [1].

**Fontes:**
- [1] Redis — Persistence › AOF disadvantages (distância 0.1266, nota 10.53)

`modelo: groq:openai/gpt-oss-120b | tokens: 1391+124 | tentativas: 1 | 2978 ms`

## q31 — É recomendado passar senhas por variáveis de ambiente no docker compose?

*Tipo: factual · deve responder · referência: Não; a documentação recomenda usar secrets.*

Não. Não se recomenda usar variáveis de ambiente para passar informações sensíveis, como senhas, para os containers; em vez disso, use *secrets* [2].

**Fontes:**
- [2] Docker Compose — Set environment variables (distância 0.1447, nota 5.36)

`modelo: groq:openai/gpt-oss-120b | tokens: 1040+120 | tentativas: 1 | 2491 ms`

## q32 — O que acontece com o IP de um container quando o compose o recria após uma mudança de configuração?

*Tipo: factual · deve responder · referência: O container antigo é removido e o novo entra na rede com outro IP, mas com o mesmo nome.*

Quando o Compose recria um container após uma mudança de configuração, ele recebe um **novo endereço IP**; o nome do serviço permanece estável. [1][3]

**Fontes:**
- [1] Docker Compose — Networking › Default network and service discovery (distância 0.1627, nota 4.97)
- [3] Docker Compose — Networking › Default network and service discovery (distância 0.1568, nota 3.49)

`modelo: groq:openai/gpt-oss-120b | tokens: 1359+184 | tentativas: 1 | 2868 ms`

## q33 — No FastAPI, uma dependência pode ter suas próprias dependências?

*Tipo: factual · deve responder · referência: Sim, o sistema de dependências é hierárquico.*

Sim. No FastAPI, uma dependência pode ter suas próprias dependências, formando uma árvore hierárquica de dependências que o sistema resolve automaticamente [1].

**Fontes:**
- [1] FastAPI — Dependencies › Dependencies › Simple and Powerful (distância 0.1583, nota 4.71)

`modelo: groq:openai/gpt-oss-120b | tokens: 999+130 | tentativas: 1 | 3762 ms`

## q34 — Como rodar o servidor de desenvolvimento de uma aplicação FastAPI?

*Tipo: procedimento · deve responder · referência: Com o comando fastapi dev.*

Execute o comando `fastapi dev` (por exemplo, `$ uv run fastapi dev`) para iniciar o servidor de desenvolvimento [1][2].

**Fontes:**
- [1] FastAPI — First Steps › First Steps › Recap (distância 0.1181, nota 9.81)
- [2] FastAPI — First Steps › First Steps (distância 0.1255, nota 9.51)

`modelo: groq:openai/gpt-oss-120b | tokens: 1340+174 | tentativas: 1 | 3933 ms`

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

* Crie uma classe que herde de `str` e `Enum` para que a documentação reconheça os valores como strings [2].
* Declare o parâmetro da rota usando a anotação do enum criado [3].
* O parâmetro receberá um membro da enum; você pode compará‑lo ou obter seu valor com `model_name.value` [4].

**Fontes:**
- [2] FastAPI — Path Parameters › Path Parameters › Predefined values (distância 0.162, nota 0.95)
- [3] FastAPI — Path Parameters › Path Parameters › Predefined values (distância 0.1624, nota 0.14)
- [4] FastAPI — Path Parameters › Path Parameters › Predefined values › Working with Python *enumerations* (distância 0.165, nota 0.12)

`modelo: groq:openai/gpt-oss-120b | tokens: 1148+304 | tentativas: 1 | 4563 ms`

## q36 — Como deixar um parâmetro de query opcional no FastAPI?

*Tipo: procedimento · deve responder · referência: Definindo o valor padrão como None.*

Para tornar um parâmetro de query opcional, basta declarar o parâmetro na função com o valor padrão `None`. Assim o FastAPI o reconhece como opcional e, caso não seja enviado na requisição, o valor será `None` [1][4].

**Fontes:**
- [1] FastAPI — Query Parameters › Query Parameters › Optional parameters (distância 0.1055, nota 10.72)
- [4] FastAPI — Query Parameters › Query Parameters (distância 0.1316, nota 6.43)

`modelo: groq:openai/gpt-oss-120b | tokens: 1113+225 | tentativas: 1 | 2823 ms`

## q37 — Como importar a aplicação no arquivo de testes quando ele fica no mesmo pacote do main.py?

*Tipo: procedimento · deve responder · referência: Com import relativo, por exemplo from .main import app.*

Use um import relativo para trazer o objeto `app` do módulo `main.py`, por exemplo:

```python
from .main import app
```

[1]

**Fontes:**
- [1] FastAPI — Testing › Testing › Separating tests › Testing file (distância 0.1121, nota 10.11)

`modelo: groq:openai/gpt-oss-120b | tokens: 1462+367 | tentativas: 1 | 4178 ms`

## q38 — Como criar uma rede no compose sem acesso externo, para isolar um banco de dados?

*Tipo: procedimento · deve responder · referência: Declarando a rede com internal: true.*

Use a rede interna declarando a opção `internal: true` no bloco `networks`. Assim a rede não tem gateway externo e os containers conectados a ela ficam inacessíveis fora do Docker Compose.

```yaml
services:
  db:
    image: postgres
    networks:
      - isolated   # conecta ao banco na rede interna

networks:
  isolated:
    internal: true   # sem conectividade externa
```

Com essa configuração o serviço `db` só pode ser alcançado por outros containers que também estejam conectados à rede `isolated`, garantindo o isolamento do banco de dados [1].

**Fontes:**
- [1] Docker Compose — Networking › Specify custom networks › Internal networks (distância 0.1606, nota 5.52)

`modelo: groq:openai/gpt-oss-120b | tokens: 1296+234 | tentativas: 1 | 3010 ms`

## q39 — Como fazer serviços de dois projetos compose diferentes conversarem entre si?

*Tipo: procedimento · deve responder · referência: Criando uma rede compartilhada uma vez e referenciando-a como external nos dois projetos.*

Crie uma rede externa compartilhada e referencie‑a em ambos os Compose files.

1. Crie a rede uma única vez:  

```bash
docker network create inter-project
```  
[1][2]

2. No *backend* Compose, declare a rede como externa e conecte o serviço a ela:  

```yaml
networks:
  shared:
    external: true
    name: inter-project
services:
  api:
    image: myapi:latest
    networks:
      - shared
      - default   # mantém a rede interna do projeto
```  
[1]

3. No *frontend* Compose, faça o mesmo:  

```yaml
networks:
  shared:
    external: true
    name: inter-project
services:
  web:
    image: myfrontend:latest
    environment:
      API_URL: http://api:8080   # usa o nome do serviço
    networks:
      - shared
```  
[1]

Com a rede externa criada antes de executar `docker compose up`, os serviços de ambos os projetos podem se alcançar pelo nome do serviço, como se estivessem no mesmo projeto.  
[2]

**Fontes:**
- [1] Docker Compose — Networking › Use an existing external network › Connecting multiple Compose projects (distância 0.1889, nota 6.53)
- [2] Docker Compose — Networking › Use an existing external network › Connecting multiple Compose projects (distância 0.2015, nota 4.81)

`modelo: groq:openai/gpt-oss-120b | tokens: 1296+420 | tentativas: 1 | 6954 ms`

## q40 — Como carregar as variáveis de ambiente de um serviço a partir de um arquivo no compose?

*Tipo: procedimento · deve responder · referência: Com o atributo env_file apontando para um arquivo .env.*

Use o atributo `env_file` no serviço do `compose.yaml` apontando para o arquivo `.env` que contém as variáveis:

```yaml
services:
  webapp:
    env_file: "webapp.env"
```

O `env_file` permite carregar as variáveis a partir de um ou mais arquivos `.env` e o caminho especificado é relativo ao diretório onde está o `compose.yaml` [3][5].

**Fontes:**
- [3] Docker Compose — Set environment variables › Use the `env_file` attribute (distância 0.1584, nota 6.15)
- [5] Docker Compose — Set environment variables › Use the `env_file` attribute (distância 0.1621, nota 4.84)

`modelo: groq:openai/gpt-oss-120b | tokens: 1028+233 | tentativas: 1 | 2766 ms`

## q41 — Como criar um índice em uma coluna de uma tabela no PostgreSQL?

*Tipo: procedimento · deve responder · referência: Com CREATE INDEX nome ON tabela (coluna).*

Use o comando `CREATE INDEX`, indicando um nome para o índice, a tabela e a coluna que será indexada. Por exemplo:

```sql
CREATE INDEX test1_id_index ON test1 (id);
```

O nome do índice pode ser escolhido livremente, facilitando a identificação posterior do seu propósito [2].

**Fontes:**
- [2] PostgreSQL 16 — Indexes: Introduction › 11.1. Introduction # (distância 0.1476, nota 6.67)

`modelo: groq:openai/gpt-oss-120b | tokens: 1457+250 | tentativas: 1 | 2749 ms`

## q42 — Como passar um servidor Redis que usa snapshots RDB para AOF sem perder dados?

*Tipo: procedimento · deve responder · referência: Habilitando o AOF com CONFIG SET no servidor em execução antes de alterar o arquivo de configuração.*

Para migrar um servidor Redis que usa snapshots RDB para AOF sem perder dados, siga o procedimento abaixo:

1. **Faça backup do dump.rdb atual** e guarde‑o em local seguro.  
   *[1][3]*

2. **Habilite o AOF no servidor em execução**:  
   ```bash
   redis-cli config set appendonly yes
   ```  
   *[2]*

3. **Opcionalmente desabilite o RDB** (para que não sejam criados novos snapshots):  
   ```bash
   redis-cli config set save ""
   ```  
   *[2]*

4. **Garanta que a mudança persista após reinício** usando `CONFIG REWRITE` ou editando `redis.conf` manualmente.  
   *[2]*

5. **Reinicie o servidor**. Ao iniciar, o Redis usará o arquivo AOF recém‑gerado para reconstruir o dataset.  
   *[2]*

6. **Verifique que as gravações estão sendo acrescentadas ao AOF** e que o número de chaves permanece o mesmo que antes da troca.  
   *[2][4]*

**Procedimento para versões mais antigas (Redis 2.0)**  

- Pare todas as gravações contra o banco.  
- Execute `redis-cli BGREWRITEAOF` para gerar o AOF a partir do dump.rdb.  
- Quando o processo terminar, edite `redis.conf` habilitando `appendonly yes`.  
- Reinicie o servidor e confirme que o número de chaves não mudou.  
  *[3]*

Seguindo esses passos, a migração de RDB para AOF ocorre sem perda de dados.

**Fontes:**
- [1] Redis — Persistence › Append-only file › How I can switch to AOF, if I'm currently using dump.rdb snapshots? (distância 0.1071, nota 10.85)
- [2] Redis — Persistence › Append-only file › How I can switch to AOF, if I'm currently using dump.rdb snapshots? (distância 0.1111, nota 10.55)
- [3] Redis — Persistence › Append-only file › How I can switch to AOF, if I'm currently using dump.rdb snapshots? (distância 0.1186, nota 8.98)
- [4] Redis — Persistence › Append-only file › How I can switch to AOF, if I'm currently using dump.rdb snapshots? (distância 0.1159, nota 8.65)

`modelo: groq:openai/gpt-oss-120b | tokens: 1182+672 | tentativas: 1 | 3834 ms`

## q43 — Tenho as rotas /users/me e /users/{user_id} no FastAPI. Em que ordem devo declará-las?

*Tipo: procedimento · deve responder · referência: /users/me antes de /users/{user_id}, porque as rotas são avaliadas em ordem.*

Você deve declarar a rota `/users/me` antes da rota `/users/{user_id}` para que o FastAPI a reconheça corretamente e não a interprete como um parâmetro `user_id` com valor `"me"` [1].

**Fontes:**
- [1] FastAPI — Path Parameters › Path Parameters › Order matters (distância 0.1192, nota 6.14)

`modelo: groq:openai/gpt-oss-120b | tokens: 1221+150 | tentativas: 1 | 3810 ms`

## q44 — O que faz a opção XX do comando EXPIRE do Redis?

*Tipo: termo_exato · deve responder · referência: Só define a expiração se a chave já tiver uma.*

A opção **XX** faz com que o tempo de expiração seja definido **apenas se a chave já possuir um tempo de expiração** [1].

**Fontes:**
- [1] Redis — EXPIRE (distância 0.1597, nota 5.76)

`modelo: groq:openai/gpt-oss-120b | tokens: 1335+113 | tentativas: 1 | 3772 ms`

## q45 — O que faz a opção GT do comando EXPIRE do Redis?

*Tipo: termo_exato · deve responder · referência: Só define a expiração se a nova for maior que a atual.*

A opção **GT** define o tempo de expiração somente quando o novo tempo especificado é maior que o tempo de expiração atual da chave; chaves sem expiração são tratadas como tendo TTL infinito para essa comparação [1].

**Fontes:**
- [1] Redis — EXPIRE (distância 0.1491, nota 5.05)

`modelo: groq:openai/gpt-oss-120b | tokens: 1142+180 | tentativas: 1 | 2596 ms`

## q46 — Para que serve o sufixo :path em um parâmetro de rota do FastAPI?

*Tipo: termo_exato · deve responder · referência: Faz o parâmetro aceitar um caminho inteiro, incluindo barras.*

O sufixo `:path` indica que o parâmetro de rota deve capturar **qualquer caminho**, inclusive barras (`/`). Assim, o parâmetro aceita valores como `/home/johndoe/myfile.txt`, permitindo que a URL contenha sub‑diretórios completos. [2]

**Fontes:**
- [2] FastAPI — Path Parameters › Path Parameters › Path parameters containing paths › Path convertor (distância 0.1484, nota 3.57)

`modelo: groq:openai/gpt-oss-120b | tokens: 1216+200 | tentativas: 1 | 3949 ms`

## q47 — O que significa condition: service_healthy no depends_on do compose?

*Tipo: termo_exato · deve responder · referência: O compose espera o healthcheck da dependência passar antes de criar o serviço.*

Sim. `condition: service_healthy` especifica que uma dependência é esperada para estar "healthy" (saudável), o que é definido pelo `healthcheck`, antes de iniciar o serviço dependente [2].

No exemplo fornecido, o serviço `db` precisa estar "healthy" (indicado pelo `healthcheck`) antes que o serviço `web` seja criado [1][3].

**Fontes:**
- [1] Docker Compose — Control startup and shutdown order › Example (distância 0.1438, nota 4.55)
- [2] Docker Compose — Control startup and shutdown order › Control startup (distância 0.1586, nota 4.22)
- [3] Docker Compose — Control startup and shutdown order › Example (distância 0.1562, nota -0.5)

`modelo: groq:qwen/qwen3.8-27b | tokens: 1268+87 | tentativas: 1 | 7805 ms`

## q48 — O que significa appendfsync everysec no Redis?

*Tipo: termo_exato · deve responder · referência: fsync a cada segundo: rápido, com risco de perder até 1 segundo de dados.*

`appendfsync everysec` indica que o Redis executa um `fsync` a cada segundo, gravando os dados no disco de forma rápida e relativamente segura; em caso de falha, pode perder até um segundo de dados [1][2].

**Fontes:**
- [1] Redis — Persistence › Append-only file › How durable is the append only file? (distância 0.1108, nota 9.73)
- [2] Redis — Persistence › Append-only file › How durable is the append only file? (distância 0.1204, nota 4.71)

`modelo: groq:openai/gpt-oss-120b | tokens: 1173+233 | tentativas: 1 | 2883 ms`

## q49 — Qual código de saída o pg_isready retorna quando o servidor está rejeitando conexões?

*Tipo: termo_exato · deve responder · referência: 1 (por exemplo, durante a inicialização).*

1 [1]

**Fontes:**
- [1] PostgreSQL 16 — pg_isready › Exit Status (distância 0.1151, nota 7.01)

`modelo: groq:openai/gpt-oss-120b | tokens: 1085+103 | tentativas: 1 | 2876 ms`

## q50 — O que é o HyperLogLog no Redis?

*Tipo: termo_exato · deve responder · referência: Estrutura que estima de forma probabilística a cardinalidade de conjuntos grandes.*

O HyperLogLog no Redis é uma estrutura de dados que fornece estimativas probabilísticas da cardinalidade (ou seja, do número de elementos) de conjuntos grandes [1]. Ele faz parte dos tipos de dados probabilísticos disponíveis no Redis, junto com Bloom filter, Count‑min sketch, entre outros [4].

**Fontes:**
- [1] Redis — Data types › Data types › HyperLogLog (distância 0.126, nota 9.81)
- [4] Redis — Data types › Data types (distância 0.1493, nota 0.46)

`modelo: groq:openai/gpt-oss-120b | tokens: 1184+167 | tentativas: 1 | 2405 ms`

## q51 — Defini uma expiração com EXPIRE no Redis. Como confiro quantos segundos ainda faltam para a chave sumir?

*Tipo: dois_docs · deve responder · referência: EXPIRE recebe o tempo em segundos; o comando TTL retorna o tempo restante.*

Não encontrei essa informação nos documentos carregados.

> Aviso: O modelo indicou que os trechos não respondem à pergunta.

**Trechos mais próximos:**
- [1] Redis — EXPIRE › Details › Appendix: Redis expires (distância 0.1389, nota 3.85)
- [2] Redis — EXPIRE › Details › Appendix: Redis expires (distância 0.1324, nota 3.41)
- [3] Redis — EXPIRE (distância 0.1382, nota 2.89)

`modelo: groq:openai/gpt-oss-120b | tokens: 1436+163 | tentativas: 1 | 2762 ms`

## q52 — Numa mesma função do FastAPI, como o framework sabe se um parâmetro vem do caminho, da query ou do corpo?

*Tipo: dois_docs · deve responder · referência: Os que estão no caminho são de rota; tipos simples fora do caminho são query; modelos Pydantic vêm do corpo.*

FastAPI analisa a assinatura da função:

* Se o parâmetro também está declarado na rota (ex.: `/items/{item_id}`), ele é tratado como **parâmetro de caminho**.  
* Se o parâmetro tem um tipo singular (`int`, `float`, `str`, `bool`, etc.), ele é interpretado como **parâmetro de query**.  
* Se o parâmetro é anotado com um **modelo Pydantic**, ele é lido do **corpo da requisição**.  

FastAPI reconhece cada um desses casos e obtém os dados do local correto [1].

**Fontes:**
- [1] FastAPI — Request Body › Request Body › Request body + path + query parameters (distância 0.1503, nota 7.03)

`modelo: groq:openai/gpt-oss-120b | tokens: 1224+340 | tentativas: 1 | 3160 ms`

## q53 — No compose, o que é um serviço e como um serviço encontra outro na rede?

*Tipo: dois_docs · deve responder · referência: Serviço é um componente da aplicação (container com sua configuração); outros serviços o encontram pelo nome na rede padrão.*

Um **serviço** no Docker Compose é o componente computacional da aplicação definido no arquivo `compose.yaml`; ele representa um conceito abstrato que, na prática, é implementado por uma ou mais instâncias do mesmo container image com a mesma configuração [4].

Um serviço **encontra** outro serviço na rede através do DNS interno que o Compose cria para a rede padrão: ao iniciar, cada contêiner registra seu nome e passa a ser resolvível pelo nome do serviço por qualquer outro contêiner conectado à mesma rede, sem necessidade de IPs ou configuração manual [2]. Links podem ser usados apenas para criar aliases adicionais, mas não são necessários para a comunicação básica [1].

**Fontes:**
- [1] Docker Compose — Networking › Link containers (distância 0.1913, nota 2.52)
- [2] Docker Compose — Networking › Default network and service discovery (distância 0.1756, nota 2.5)
- [4] Docker Compose — How Compose works (distância 0.1782, nota 1.26)

`modelo: groq:openai/gpt-oss-120b | tokens: 1202+366 | tentativas: 1 | 3290 ms`

## q54 — Como habilitar CORS em uma API FastAPI?

*Tipo: sem_resposta · NÃO deve responder · referência: Não está nos documentos carregados.*

Não encontrei essa informação nos documentos carregados.

> Aviso: Trechos mais próximos, abaixo do limiar de relevância.

**Trechos mais próximos:**
- [1] FastAPI — First Steps › First Steps › Deploy your app (optional) (distância 0.1549, nota 0.3)
- [2] FastAPI — Dependencies › Dependencies › First Steps › Declare the dependency, in the "dependant" (distância 0.1557, nota -0.22)
- [3] FastAPI — First Steps › First Steps › `fastapi dev` with path or with `--entrypoint` CLI option (distância 0.1571, nota -0.44)

`modelo: None | tokens: 0+0 | tentativas: 0 | 2914 ms`

## q55 — Como configurar replicação streaming entre dois servidores PostgreSQL?

*Tipo: sem_resposta · NÃO deve responder · referência: Não está nos documentos.*

Não encontrei essa informação nos documentos carregados.

> Aviso: Trechos mais próximos, abaixo do limiar de relevância.

**Trechos mais próximos:**
- [1] PostgreSQL 16 — pg_isready › Options (distância 0.1789, nota -1.62)
- [2] Docker Compose — Networking › Debugging (distância 0.1843, nota -2.04)
- [3] PostgreSQL 16 — pg_isready › Options (distância 0.1904, nota -2.54)

`modelo: None | tokens: 0+0 | tentativas: 0 | 1469 ms`

## q56 — Como limitar a memória e a CPU de um serviço no docker compose?

*Tipo: sem_resposta · NÃO deve responder · referência: Não está nos documentos.*

Não encontrei essa informação nos documentos carregados.

> Aviso: Trechos mais próximos, abaixo do limiar de relevância.

**Trechos mais próximos:**
- [1] Docker Compose — How Compose works (distância 0.1579, nota 1.47)
- [2] Docker Compose — How Compose works › CLI › Key commands (distância 0.1422, nota 1.23)
- [3] Docker Compose — Networking › Debugging (distância 0.1635, nota 0.11)

`modelo: None | tokens: 0+0 | tentativas: 0 | 1731 ms`

## q57 — Como receber upload de arquivos em uma rota FastAPI?

*Tipo: sem_resposta · NÃO deve responder · referência: Não está nos documentos carregados.*

Não encontrei essa informação nos documentos carregados.

> Aviso: Trechos mais próximos, abaixo do limiar de relevância.

**Trechos mais próximos:**
- [1] FastAPI — First Steps › First Steps › Recap, step by step › Step 4: define the path operation function (distância 0.154, nota 1.01)
- [2] FastAPI — First Steps › First Steps › `fastapi dev` with path or with `--entrypoint` CLI option (distância 0.1537, nota 0.75)
- [3] FastAPI — Dependencies › Dependencies › First Steps › Declare the dependency, in the "dependant" (distância 0.164, nota 0.25)

`modelo: None | tokens: 0+0 | tentativas: 0 | 2847 ms`

## q58 — Qual a diferença entre VACUUM e VACUUM FULL no PostgreSQL?

*Tipo: sem_resposta · NÃO deve responder · referência: Não está nos documentos.*

Não encontrei essa informação nos documentos carregados.

> Aviso: Trechos mais próximos, abaixo do limiar de relevância.

**Trechos mais próximos:**
- [1] PostgreSQL 16 — Character Types › 8.3. Character Types # (distância 0.1864, nota -0.51)
- [2] PostgreSQL 16 — Character Types › 8.3. Character Types # › Tip (distância 0.1829, nota -0.89)
- [3] PostgreSQL 16 — Character Types › 8.3. Character Types # (distância 0.1824, nota -1.71)

`modelo: None | tokens: 0+0 | tentativas: 0 | 1816 ms`

## q59 — Como enviar um e-mail em segundo plano depois de responder uma requisição no FastAPI?

*Tipo: sem_resposta · NÃO deve responder · referência: Não está nos documentos carregados.*

Não encontrei essa informação nos documentos carregados.

> Aviso: Trechos mais próximos, abaixo do limiar de relevância.

**Trechos mais próximos:**
- [1] FastAPI — Request Body › Request Body (distância 0.1628, nota 0.68)
- [2] FastAPI — First Steps › First Steps (distância 0.1606, nota -0.44)
- [3] FastAPI — Query Parameters › Query Parameters (distância 0.1624, nota -1.05)

`modelo: None | tokens: 0+0 | tentativas: 0 | 3276 ms`

## q60 — Como criar um usuário e conceder permissões com GRANT no PostgreSQL?

*Tipo: sem_resposta · NÃO deve responder · referência: Não está nos documentos.*

Não encontrei essa informação nos documentos carregados.

> Aviso: Trechos mais próximos, abaixo do limiar de relevância.

**Trechos mais próximos:**
- [1] FastAPI — Dependencies › Dependencies › Simple and Powerful (distância 0.184, nota -0.92)
- [2] PostgreSQL 16 — Indexes: Introduction › 11.1. Introduction # (distância 0.1946, nota -2.16)
- [3] PostgreSQL 16 — Indexes: Introduction › 11.1. Introduction # (distância 0.2035, nota -2.2)

`modelo: None | tokens: 0+0 | tentativas: 0 | 1958 ms`
