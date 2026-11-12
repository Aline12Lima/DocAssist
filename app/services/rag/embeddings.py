"""Modelos de embedding: um lugar só para o nome, os prefixos e a normalização.

O e5 espera "query: " na pergunta e "passage: " em cada trecho guardado. Esquecer os
prefixos é o erro mais comum com esse modelo, por isso eles só existem aqui.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class ConfigModelo:
    nome: str  # nome no Hugging Face
    apelido: str  # entra no nome da coleção: docs_<apelido>_v1
    prefixo_consulta: str = ""
    prefixo_trecho: str = ""
    max_tokens: int = 256


MODELOS = {
    "minilm": ConfigModelo("sentence-transformers/all-MiniLM-L6-v2", "minilm", max_tokens=256),
    "e5small": ConfigModelo(
        "intfloat/multilingual-e5-small", "e5small", "query: ", "passage: ", max_tokens=512
    ),
}


class Embedder:
    """Transforma textos em vetores normalizados, aplicando os prefixos do modelo."""

    def __init__(self, config: ConfigModelo, modelo=None):
        self.config = config
        self._modelo = modelo  # nos testes, um modelo falso entra aqui

    @property
    def modelo(self):
        if self._modelo is None:
            from sentence_transformers import SentenceTransformer  # carrega só quando usar

            self._modelo = SentenceTransformer(self.config.nome)
        return self._modelo

    def vetorizar_trechos(self, textos: list[str]) -> list[list[float]]:
        com_prefixo = [self.config.prefixo_trecho + texto for texto in textos]
        vetores = self.modelo.encode(com_prefixo, batch_size=32, normalize_embeddings=True)
        return vetores.tolist()

    def vetorizar_consulta(self, texto: str) -> list[float]:
        vetor = self.modelo.encode(self.config.prefixo_consulta + texto, normalize_embeddings=True)
        return vetor.tolist()

    def contar_tokens(self, texto: str) -> int:
        # verbose=False: só contamos, então o aviso de "texto longo demais" não se aplica
        return len(self.modelo.tokenizer.encode(texto, add_special_tokens=False, verbose=False))


_embedders: dict[str, Embedder] = {}


def obter_embedder(chave: str) -> Embedder:
    """Devolve o Embedder do modelo (minilm ou e5small), carregado uma vez só."""
    if chave not in MODELOS:
        raise ValueError(f"Modelo desconhecido: {chave}. Opções: {', '.join(MODELOS)}")
    if chave not in _embedders:
        _embedders[chave] = Embedder(MODELOS[chave])
    return _embedders[chave]
