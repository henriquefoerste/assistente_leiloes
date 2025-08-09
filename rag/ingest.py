import os
import fitz  # PyMuPDF
import faiss
import pickle
import json
from sentence_transformers import SentenceTransformer

DATA_DIR = "../leiloes"  # Diretório dos leilões coletados
INDEX_DIR = "index"
MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
EMBEDDING_SIZE = 384

def load_metadata(metadata_path):
    """Carrega metadados de um leilão."""
    try:
        with open(metadata_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"[AVISO] Erro ao carregar metadata {metadata_path}: {e}")
        return {}

def extract_text_chunks(pdf_path, metadata, chunk_size=700, overlap=150):
    """Extrai chunks de texto de um PDF com metadados enriquecidos."""
    try:
        doc = fitz.open(pdf_path)
        chunks = []
        
        for page_num, page in enumerate(doc, start=1):
            text = page.get_text("text")
            words = text.split()
            
            if not words:  # Pular páginas vazias
                continue
                
            step = chunk_size - overlap
            for start in range(0, len(words), step):
                chunk_text = " ".join(words[start:start+chunk_size])
                
                # Criar chunk enriquecido com metadados
                chunk = {
                    "doc_id": os.path.basename(pdf_path),
                    "leilao_folder": os.path.basename(os.path.dirname(pdf_path)),
                    "page": page_num,
                    "text": chunk_text,
                    # Metadados do leilão
                    "leilao_id": metadata.get('leilao_id', ''),
                    "codigo_zuk": metadata.get('codigo_zuk', ''),
                    "preco": metadata.get('preco', ''),
                    "tipo_imovel": metadata.get('tipo_imovel', ''),
                    "cidade": metadata.get('cidade', ''),
                    "bairro": metadata.get('bairro', ''),
                    "endereco_completo": metadata.get('endereco_completo', ''),
                    "comitente": metadata.get('comitente', ''),
                    "url": metadata.get('url', ''),
                }
                chunks.append(chunk)
        
        doc.close()
        return chunks
        
    except Exception as e:
        print(f"[ERRO] Erro ao processar PDF {pdf_path}: {e}")
        return []

def main():
    print("[INFO] Iniciando indexação dos leilões...")
    os.makedirs(INDEX_DIR, exist_ok=True)
    
    # Carregar modelo de embeddings
    print("[INFO] Carregando modelo de embeddings...")
    model = SentenceTransformer(MODEL_NAME)
    
    all_chunks = []
    processed_leiloes = 0
    processed_pdfs = 0
    
    # Percorrer todas as pastas de leilões
    if not os.path.exists(DATA_DIR):
        print(f"[ERRO] Diretório {DATA_DIR} não encontrado!")
        return
    
    leilao_folders = [f for f in os.listdir(DATA_DIR) if f.startswith('leilao_')]
    print(f"[INFO] Encontradas {len(leilao_folders)} pastas de leilões")
    
    for leilao_folder in leilao_folders:
        leilao_path = os.path.join(DATA_DIR, leilao_folder)
        
        if not os.path.isdir(leilao_path):
            continue
            
        print(f"[INFO] Processando: {leilao_folder}")
        
        # Carregar metadados do leilão
        metadata_path = os.path.join(leilao_path, "metadata.json")
        metadata = load_metadata(metadata_path) if os.path.exists(metadata_path) else {}
        
        # Processar todos os PDFs na pasta
        pdf_files = [f for f in os.listdir(leilao_path) if f.lower().endswith('.pdf')]
        
        for pdf_file in pdf_files:
            pdf_path = os.path.join(leilao_path, pdf_file)
            print(f"  - Extraindo texto de: {pdf_file}")
            
            chunks = extract_text_chunks(pdf_path, metadata)
            all_chunks.extend(chunks)
            processed_pdfs += 1
        
        processed_leiloes += 1
    
    if not all_chunks:
        print("[AVISO] Nenhum chunk extraído! Verifique se há PDFs nas pastas dos leilões.")
        return
    
    print(f"[INFO] Total extraído:")
    print(f"  - {processed_leiloes} leilões processados")
    print(f"  - {processed_pdfs} PDFs processados") 
    print(f"  - {len(all_chunks)} chunks de texto extraídos")
    
    # Gerar embeddings
    print("[INFO] Gerando embeddings...")
    texts = [c["text"] for c in all_chunks]
    vectors = model.encode(texts, show_progress_bar=True)
    
    # Criar índice FAISS
    print("[INFO] Criando índice FAISS...")
    index = faiss.IndexFlatL2(EMBEDDING_SIZE)
    index.add(vectors)
    
    # Salvar arquivos
    print("[INFO] Salvando índice e metadados...")
    faiss.write_index(index, os.path.join(INDEX_DIR, "faiss.index"))
    
    with open(os.path.join(INDEX_DIR, "chunks.pkl"), "wb") as f:
        pickle.dump(all_chunks, f)
    
    print(f"[SUCESSO] Índice criado com {len(all_chunks)} chunks!")
    print(f"[INFO] Arquivos salvos em: {INDEX_DIR}/")
    
    # Estatísticas
    tipos_imoveis = {}
    cidades = {}
    for chunk in all_chunks:
        tipo = chunk.get('tipo_imovel', 'Não informado')
        cidade = chunk.get('cidade', 'Não informado')
        tipos_imoveis[tipo] = tipos_imoveis.get(tipo, 0) + 1
        cidades[cidade] = cidades.get(cidade, 0) + 1
    
    print(f"\n[ESTATÍSTICAS]")
    print(f"Tipos de imóveis mais comuns:")
    for tipo, count in sorted(tipos_imoveis.items(), key=lambda x: x[1], reverse=True)[:5]:
        print(f"  - {tipo}: {count} chunks")
    
    print(f"Cidades mais comuns:")
    for cidade, count in sorted(cidades.items(), key=lambda x: x[1], reverse=True)[:5]:
        print(f"  - {cidade}: {count} chunks")

if __name__ == "__main__":
    main()
