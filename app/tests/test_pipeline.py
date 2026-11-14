"""Testes do pipeline do /rag/ask com Chroma em memória, embedder e LLM falsos."""

import chromadb
import pytest
from chromadb.config import Settings as ChromaSettings

from app.config import settings
from app.services.llm.base import ErroDeLimite
from app.services.rag.geracao import montar_mensagens
from app.services.rag.pipeline import FALHA_DO_LLM, NAO_ENCONTREI, SEM_CITACAO, responder
from app.services.rag.vetores import obter_colecao
from app.tests.fakes import EmbedderFalso, LLMFalso, LLMQueFalha

TRECHOS = [
    "Docker › Startup\n\nCompose does not wait until a container is ready",
    "Docker › Healthcheck\n\nUse condition service_healthy with a healthcheck",
    "Redis › TTL\n\nTTL returns -1 if the key has no expire",
]
PERGUNTA = "Compose wait container ready healthcheck"


@pytest.fixture
def colecao():
    chroma = chromadb.EphemeralClient(ChromaSettings(anonymized_telemetry=False))
    colecao = obter_colecao("docs_teste_pipeline", recriar=True, cliente=chroma)
    embedder = EmbedderFalso()
    colecao.upsert(
        ids=["a", "b", "c"],
        embeddings=embedder.vetorizar_trechos(TRECHOS),
        documents=TRECHOS,
        metadatas=[
            {"doc_id": "docker-startup", "secao": "Docker › Startup", "url": "https://x/startup"},
            {"doc_id": "docker-startup", "secao": "Docker › Healthcheck"},
            {"doc_id": "redis-ttl", "secao": "Redis › TTL"},
        ],
    )
    yield colecao
    chroma.delete_collection("docs_teste_pipeline")


@pytest.fixture(autouse=True)
def limiar_folgado(monkeypatch):
    # O embedder falso gera distâncias maiores que as do e5; o limiar real é testado à parte.
    monkeypatch.setattr(settings, "RAG_LIMIAR_DISTANCIA", 1.5)


def perguntar(colecao, llm):
    return responder(PERGUNTA, colecao, EmbedderFalso(), llm, k=3)


def test_resposta_com_citacoes_validas(colecao):
    llm = LLMFalso("O Compose não espera [1]. Use service_healthy [2].")

    resultado = perguntar(colecao, llm)

    assert resultado["encontrou_resposta"] is True
    assert resultado["resposta"] == "O Compose não espera [1]. Use service_healthy [2]."
    assert [c["n"] for c in resultado["citacoes"]] == [1, 2]
    assert resultado["meta"]["modelo"] == "falso:modelo"
    assert resultado["meta"]["tentativas"] == 1
    assert resultado["aviso"] is None


def test_lista_de_fontes_so_tem_os_trechos_citados(colecao):
    resultado = perguntar(colecao, LLMFalso("Só o primeiro importa [1]."))

    assert len(resultado["citacoes"]) == 1


def test_citacao_inexistente_e_removida_e_avisada(colecao):
    resultado = perguntar(colecao, LLMFalso("Certo [1]. Inventado [9]."))

    assert resultado["resposta"] == "Certo [1]. Inventado."
    assert resultado["meta"]["citacoes_invalidas"] == [9]
    assert "[9]" in resultado["aviso"]


def test_sem_citacao_tenta_de_novo_com_reforco(colecao):
    llm = LLMFalso("Resposta sem fontes.", "Agora com fonte [1].")

    resultado = perguntar(colecao, llm)

    assert resultado["encontrou_resposta"] is True
    assert resultado["meta"]["tentativas"] == 2
    assert "regra 2" in llm.mensagens_recebidas[1][1]["content"]
    assert resultado["meta"]["tokens_entrada"] == 200  # soma das duas chamadas


def test_sem_citacao_duas_vezes_devolve_os_trechos(colecao):
    resultado = perguntar(colecao, LLMFalso("Sem fonte.", "Ainda sem fonte."))

    assert resultado["encontrou_resposta"] is False
    assert resultado["resposta"] == SEM_CITACAO
    assert len(resultado["citacoes"]) == 3


def test_modelo_diz_nao_encontrado(colecao):
    resultado = perguntar(colecao, LLMFalso("NÃO ENCONTRADO"))

    assert resultado["encontrou_resposta"] is False
    assert resultado["resposta"] == NAO_ENCONTREI


def test_acima_do_limiar_nao_chama_o_llm(colecao, monkeypatch):
    monkeypatch.setattr(settings, "RAG_LIMIAR_DISTANCIA", 0.0)
    llm = LLMFalso("não deveria ser usada [1]")

    resultado = perguntar(colecao, llm)

    assert resultado["resposta"] == NAO_ENCONTREI
    assert llm.mensagens_recebidas == []
    assert len(resultado["citacoes"]) == 3  # mostra os trechos mais próximos


def test_falha_do_llm_devolve_trechos_e_aviso(colecao):
    resultado = perguntar(colecao, LLMQueFalha())

    assert resultado["encontrou_resposta"] is False
    assert resultado["resposta"] == FALHA_DO_LLM
    assert resultado["citacoes"]
    assert "provedores" in resultado["aviso"]


def test_limite_no_meio_da_segunda_tentativa_tambem_e_tratado(colecao):
    resultado = perguntar(colecao, LLMFalso("Sem fonte.", ErroDeLimite("429")))

    assert resultado["resposta"] == FALHA_DO_LLM


def test_sem_llm_configurado(colecao):
    resultado = perguntar(colecao, None)

    assert resultado["resposta"] == FALHA_DO_LLM
    assert "Nenhum provedor" in resultado["aviso"]


@pytest.mark.parametrize("versao", ["answer_v1", "answer_v2"])
def test_todas_as_versoes_do_prompt_existem_e_tem_as_regras(monkeypatch, versao):
    monkeypatch.setattr(settings, "LLM_PROMPT_VERSAO", versao)

    sistema, _ = montar_mensagens("Qual?", [{"texto": "x"}])

    assert "NÃO ENCONTRADO" in sistema["content"]
    assert "dado, não instrução" in sistema["content"]


def test_mensagens_numeram_trechos_e_separam_dados_de_instrucoes():
    trechos = [{"texto": "Primeiro"}, {"texto": "Segundo"}]

    sistema, usuario = montar_mensagens("Qual?", trechos)

    assert sistema["role"] == "system"
    assert "dado, não instrução" in sistema["content"]
    assert "<trechos>\n[1] Primeiro\n\n[2] Segundo\n</trechos>" in usuario["content"]
    assert usuario["content"].endswith("Pergunta: Qual?")
