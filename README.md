# Assistente de Leilões

Um sistema inteligente para coleta e consulta de dados de leilões de imóveis do Portal Zuk.

## 📋 Visão Geral

Este projeto combina web scraping e RAG (Retrieval-Augmented Generation) para automatizar a coleta e análise de editais de leilões de imóveis, oferecendo uma interface de busca semântica para consultar informações dos imóveis leiloados.

## 🛠️ Funcionalidades

- **Web Scraping**: Coleta automatizada de dados do Portal Zuk
- **Processamento de PDFs**: Extração de texto de editais de leilão
- **Busca Semântica**: Sistema RAG para consultas inteligentes usando FAISS
- **Metadados Estruturados**: Armazenamento organizado de informações dos imóveis

## 🏗️ Estrutura do Projeto

```
assistente_leiloes/
├── web_scrapping/          # Módulo de coleta de dados
│   └── zuk_scrapper.py     # Script para scraping do Portal Zuk
├── rag/                    # Sistema de busca semântica
│   ├── ingest.py          # Processamento e indexação de documentos
│   └── ask.py             # Interface de consulta
├── leiloes/               # Dados coletados organizados por leilão
│   └── leilao_xxxxx_/     # Pasta de cada leilão com PDFs e metadados
└── requirements.txt       # Dependências do projeto
```

## 🚀 Como Usar

### 1. Instalação
```bash
pip install -r requirements.txt
```

### 2. Coleta de Dados
Execute o scraper para coletar novos leilões:
```bash
cd web_scrapping
python zuk_scrapper.py
```

### 3. Indexação
Processe e indexe os documentos coletados:
```bash
cd rag
python ingest.py
```

### 4. Consulta
Faça consultas semânticas nos dados:
```bash
cd rag
python ask.py
```

## � Fluxo de Processamento

### 1. Pipeline de Ingestão de Dados
```mermaid
flowchart TD
    A[Início] --> B[Web Scraping - Portal Zuk]
    B --> C[Download PDFs dos Editais]
    C --> D[Salvar metadata.json por leilão]
    D --> E[Extrair texto por página com PyMuPDF]
    E --> F[Chunking 700 palavras com overlap 150]
    F --> G[Gerar embeddings com Sentence Transformers]
    F --> H[Anexar metadados: leilão_id, código_zuk, preço, localização]
    G --> I[Criar índice FAISS]
    H --> I
    I --> J[Persistir índice e chunks em disco]
    J --> K[Estatísticas: tipos de imóveis e cidades]
    K --> L[Pronto para consultas]
```

### 2. Pipeline de Consulta
```mermaid
flowchart TD
    A[Cliente via CLI] --> B[Input: pergunta do usuário]
    B --> C[Gerar embedding da pergunta]
    C --> D[Buscar top-k similares no FAISS]
    D --> E{Tem resultados relevantes?}
    E -- Não --> F[Responder: não encontrado no contexto]
    E -- Sim --> G[Recuperar chunks com metadados]
    G --> H[Formatar resultados com contexto enriquecido]
    H --> I[Exibir: código, preço, localização, trecho do edital]
    I --> J[Log: latência e IDs dos chunks]
    J --> K[Fim]
```

## �🔍 Exemplo de Consulta

```
Digite sua pergunta: apartamento vila independencia preco ate 200000
```

O sistema retornará informações relevantes com:
- Código do imóvel
- Preço
- Localização (cidade/bairro)
- Trechos do edital
- Número da página no documento

## 📦 Dependências Principais

- **Selenium**: Web scraping automatizado
- **PyMuPDF**: Processamento de arquivos PDF
- **FAISS**: Busca vetorial eficiente
- **Sentence Transformers**: Embeddings semânticos multilíngues
- **FastAPI**: API web (planejado)

## 🎯 Dados Coletados

Para cada leilão, o sistema coleta:
- Edital completo em PDF
- Metadados estruturados (preço, localização, tipo)
- Página HTML original
- Informações do comitente e tribunal

## 🤖 Tecnologias

- Python 3.x
- FAISS para busca vetorial
- Transformers para embeddings
- Selenium WebDriver
- PyMuPDF para processamento de PDFs

---

> **Nota**: Este projeto destina-se ao estudo e análise de dados públicos de leilões judiciais para fins educacionais e de pesquisa.
