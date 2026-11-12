"""Compara o MiniLM com o multilingual-e5-small na mesma busca, em português e em inglês.

Uso:
    docker compose exec api python scripts/estudo_embeddings.py
"""

from sentence_transformers import SentenceTransformer

# nome no Hugging Face, prefixo da pergunta, prefixo do trecho
MODELOS = {
    "MiniLM (atual)": ("sentence-transformers/all-MiniLM-L6-v2", "", ""),
    "e5-small (multilíngue)": ("intfloat/multilingual-e5-small", "query: ", "passage: "),
}

FRASES = [
    "Docker compose sobe vários containers com um comando",
    "Um container empacota a aplicação e suas dependências",
    "Use docker ps para listar os containers em execução",
    "Asse o bolo de cenoura por 40 minutos",
    "Misture farinha, ovos e açúcar numa tigela",
]

PERGUNTAS = ["como subir containers", "how to start containers"]


def main():
    for nome, (caminho, prefixo_pergunta, prefixo_trecho) in MODELOS.items():
        modelo = SentenceTransformer(caminho)
        vetores = modelo.encode(
            [prefixo_trecho + frase for frase in FRASES], normalize_embeddings=True
        )

        for pergunta in PERGUNTAS:
            vetor_pergunta = modelo.encode(prefixo_pergunta + pergunta, normalize_embeddings=True)
            # Com vetores normalizados, o produto escalar já é o cosseno.
            similaridades = vetores @ vetor_pergunta

            print(f"\n{nome} — pergunta: {pergunta}")
            for similaridade, frase in sorted(
                zip(similaridades, FRASES, strict=True), reverse=True
            ):
                print(f"  {similaridade:.3f}  {frase}")


if __name__ == "__main__":
    main()
