import faiss
import pickle
from sentence_transformers import SentenceTransformer

INDEX_DIR = "index"
MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

def search(query, top_k=5):
    model = SentenceTransformer(MODEL_NAME)
    index = faiss.read_index(f"{INDEX_DIR}/faiss.index")
    with open(f"{INDEX_DIR}/chunks.pkl", "rb") as f:
        chunks = pickle.load(f)
    query_vec = model.encode([query])
    D, I = index.search(query_vec, top_k)
    results = []
    for idx in I[0]:
        results.append(chunks[idx])
    return results

def format_result(chunk):
    """Formata um resultado de busca de forma mais legível."""
    header = f"[{chunk['doc_id']} - pág. {chunk['page']}]"
    
    if chunk.get('codigo_zuk'):
        header += f" Código: {chunk['codigo_zuk']}"
    
    if chunk.get('preco'):
        header += f" | Preço: R$ {chunk['preco']}"
    
    if chunk.get('cidade') and chunk.get('bairro'):
        header += f" | {chunk['cidade']} - {chunk['bairro']}"
    
    text_preview = chunk['text'][:300] + "..." if len(chunk['text']) > 300 else chunk['text']
    
    return f"{header}\n{text_preview}\n{'-'*80}"

if __name__ == "__main__":
    q = input("Digite sua pergunta: ")
    hits = search(q)
    print(f"\n=== Resultados para: '{q}' ===\n")
    
    for i, h in enumerate(hits, 1):
        print(f"RESULTADO {i}:")
        print(format_result(h))
        print()
