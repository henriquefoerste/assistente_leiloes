import faiss
import pickle
import torch
from transformers import AutoModel, AutoTokenizer
import numpy as np

INDEX_DIR = "index"
MODEL_NAME = "deepseek-ai/deepseek-coder-1.3b-base"

# Carregar modelo e tokenizer globalmente (mais eficiente)
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
model = AutoModel.from_pretrained(MODEL_NAME)

def get_embedding(text):
    """Gera embedding usando DeepSeek"""
    inputs = tokenizer(text, return_tensors="pt", truncation=True, max_length=512)
    with torch.no_grad():
        outputs = model(**inputs)
    # Usar mean pooling do último hidden state
    embeddings = outputs.last_hidden_state.mean(dim=1)
    return embeddings.numpy()

def search(query, top_k=10):
    index = faiss.read_index(f"{INDEX_DIR}/faiss.index")
    with open(f"{INDEX_DIR}/chunks.pkl", "rb") as f:
        chunks = pickle.load(f)
    
    query_vec = get_embedding(query)
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