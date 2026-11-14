"""Confere as chaves de LLM: lista os modelos de cada provedor e testa a cadeia configurada.

Uso:
    python -m scripts.testar_llm

Nunca mostra as chaves, só se elas existem.
"""

import time

from app.config import settings
from app.services.llm.base import ErroDoProvedor
from app.services.llm.cadeia import URLS, chave_do_provedor, ler_lista_de_modelos
from app.services.llm.compativel_openai import ProvedorCompativelOpenAI

PALAVRAS_DE_OUTROS_TIPOS = ("whisper", "tts", "guard", "embed", "imagen", "veo", "audio", "aqa")


def listar_modelos():
    print("== Modelos disponíveis para as suas chaves\n")
    for provedor, url in URLS.items():
        chave = chave_do_provedor(provedor)
        if not chave:
            print(f"{provedor}: sem chave no .env (pulado)\n")
            continue
        try:
            modelos = ProvedorCompativelOpenAI(provedor, url, chave, "-").listar_modelos()
        except Exception as erro:  # noqa: BLE001 - qualquer falha aqui só é mostrada
            print(f"{provedor}: erro ao listar modelos ({erro})\n")
            continue
        texto = [m for m in modelos if not any(p in m.lower() for p in PALAVRAS_DE_OUTROS_TIPOS)]
        print(f"{provedor}: {len(texto)} modelos de texto")
        for modelo in texto:
            print(f"  {provedor}:{modelo.removeprefix('models/')}")
        print()


def testar_cadeia():
    print(f"== Testando LLM_MODELOS = {settings.LLM_MODELOS}\n")
    mensagens = [{"role": "user", "content": "Responda apenas com a palavra: funcionando"}]
    for provedor, modelo in ler_lista_de_modelos(settings.LLM_MODELOS):
        chave = chave_do_provedor(provedor)
        if provedor not in URLS or not chave:
            print(f"PULADO  {provedor}:{modelo} (provedor desconhecido ou sem chave)")
            continue
        llm = ProvedorCompativelOpenAI(provedor, URLS[provedor], chave, modelo)
        inicio = time.perf_counter()
        try:
            resposta = llm.gerar(mensagens, max_tokens=200, temperatura=0)
        except ErroDoProvedor as erro:
            print(f"ERRO    {erro}")
            continue
        segundos = time.perf_counter() - inicio
        print(
            f"ok      {resposta.modelo}: {resposta.texto[:40]!r} "
            f"({resposta.tokens_entrada}+{resposta.tokens_saida} tokens, {segundos:.1f}s)"
        )


if __name__ == "__main__":
    listar_modelos()
    testar_cadeia()
