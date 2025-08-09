from fastapi import FastAPI
from pydantic import BaseModel
import faiss
import pickle
from sentence_transformers import SentenceTransformer

INDEX_DIR = "index"
MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

app = FastAPI()
model = SentenceTransformer(MODEL_NAME)
index = faiss.read_index(f"{INDEX_DIR}/faiss.index")
with open(f"{INDEX_DIR}/chunks.pkl", "rb") as f:
    chunks = pickle.load(f)

class Question(BaseModel):
    question: str
    top_k: int = 5
    filter_cidade: str = None
    filter_tipo_imovel: str = None
    max_preco: float = None

@app.post("/ask")
def ask(q: Question):
    query_vec = model.encode([q.question])
    D, I = index.search(query_vec, q.top_k * 2)  # Buscar mais para filtrar depois
    
    results = []
    for idx in I[0]:
        chunk = chunks[idx]
        
        # Aplicar filtros se especificados
        if q.filter_cidade and chunk.get('cidade', '').lower() != q.filter_cidade.lower():
            continue
        if q.filter_tipo_imovel and chunk.get('tipo_imovel', '').lower() != q.filter_tipo_imovel.lower():
            continue
        if q.max_preco and chunk.get('preco'):
            try:
                preco = float(chunk['preco'])
                if preco > q.max_preco:
                    continue
            except:
                pass
        
        results.append(chunk)
        
        # Parar quando atingir o número desejado de resultados
        if len(results) >= q.top_k:
            break
    
    return {
        "question": q.question,
        "total_results": len(results),
        "filters_applied": {
            "cidade": q.filter_cidade,
            "tipo_imovel": q.filter_tipo_imovel,
            "max_preco": q.max_preco
        },
        "results": results
    }

@app.get("/stats")
def get_stats():
    """Endpoint para obter estatísticas do índice."""
    tipos_imoveis = {}
    cidades = {}
    precos = []
    
    for chunk in chunks:
        if chunk.get('tipo_imovel'):
            tipo = chunk['tipo_imovel']
            tipos_imoveis[tipo] = tipos_imoveis.get(tipo, 0) + 1
        
        if chunk.get('cidade'):
            cidade = chunk['cidade']
            cidades[cidade] = cidades.get(cidade, 0) + 1
        
        if chunk.get('preco'):
            try:
                preco = float(chunk['preco'])
                precos.append(preco)
            except:
                pass
    
    return {
        "total_chunks": len(chunks),
        "tipos_imoveis": dict(sorted(tipos_imoveis.items(), key=lambda x: x[1], reverse=True)),
        "cidades": dict(sorted(cidades.items(), key=lambda x: x[1], reverse=True)),
        "preco_stats": {
            "min": min(precos) if precos else 0,
            "max": max(precos) if precos else 0,
            "avg": sum(precos) / len(precos) if precos else 0,
            "total_com_preco": len(precos)
        }
    }
