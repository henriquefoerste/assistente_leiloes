from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
import time
from webdriver_manager.chrome import ChromeDriverManager
from time import sleep
import os
import json
import requests
from urllib.parse import urlparse
import re

def highlight(element, driver):
    """Destaca um elemento visualmente com borda vermelha."""
    driver.execute_script("arguments[0].style.border='3px solid red'; arguments[0].style.background='yellow';", element)

def close_modal(driver):
    """Tenta fechar o modal de virada se estiver presente."""
    try:
        close_button = driver.find_element(By.ID, "close-modal-virada")
        close_button.click()
        time.sleep(1)
    except Exception as e:
        print(f"[AVISO] Modal não encontrado ou erro ao fechar: {e}")

def open_zukpage(driver):
    """Abre a página de imóveis do Portal Zuk."""
    driver.get("https://www.portalzuk.com.br/leilao-de-imoveis/u/todos-imoveis/sp")
    time.sleep(3)  # Aguardar carregamento inicial
    close_modal(driver)  # Tenta fechar modal se existir
    time.sleep(2)


def find_property_cards(driver):
    """Encontra o primeiro card de imóvel na página."""
    cards = driver.find_elements(By.CLASS_NAME, "card-property")
    return cards if cards else None




def extract_property_metadata(driver):
    """Extrai metadados do imóvel na página atual usando dataLayer."""
    metadata = {}
    
    try:
        # Extrair dados do dataLayer JavaScript
        script = """
        return window.dataLayer && window.dataLayer[0] ? window.dataLayer[0] : {};
        """
        data_layer = driver.execute_script(script)
        
        if data_layer:
            metadata.update({
                'leilao_id': data_layer.get('leilaoId', ''),
                'codigo_zuk': data_layer.get('codZ', ''),
                'product_id': data_layer.get('productId', ''),
                'preco': data_layer.get('price', ''),
                'tipo_imovel': data_layer.get('tipoImovel', ''),
                'uf': data_layer.get('uf', ''),
                'cidade': data_layer.get('cidade', ''),
                'bairro': data_layer.get('bairro', ''),
                'comitente': data_layer.get('comitente', ''),
            })
        
        # Extrair título da página
        try:
            metadata['titulo'] = driver.find_element(By.TAG_NAME, "title").get_attribute("innerHTML")
        except:
            metadata['titulo'] = ""
        
        # Extrair endereço da meta description
        try:
            meta_desc = driver.find_element(By.CSS_SELECTOR, 'meta[name="description"]').get_attribute("content")
            # Extrair endereço da descrição usando regex
            endereco_match = re.search(r'- ([^-]+) - \.\. -', meta_desc)
            if endereco_match:
                metadata['endereco_completo'] = endereco_match.group(1).strip()
            else:
                metadata['endereco_completo'] = ""
        except:
            metadata['endereco_completo'] = ""
        
        # URL atual
        metadata['url'] = driver.current_url
        
        # Buscar links de documentos PDF
        pdf_links = []
        try:
            pdf_elements = driver.find_elements(By.CSS_SELECTOR, "a[href*='.pdf']")
            for element in pdf_elements:
                href = element.get_attribute("href")
                if href and ".pdf" in href:
                    # Extrair o texto do label do documento
                    try:
                        label = element.find_element(By.CSS_SELECTOR, ".property-documents-item-label").text
                    except:
                        label = "Documento"
                    
                    pdf_links.append({
                        'url': href,
                        'label': label,
                        'filename': os.path.basename(urlparse(href).path)
                    })
        except Exception as e:
            print(f"[AVISO] Erro ao buscar PDFs: {e}")
        
        metadata['documentos_pdf'] = pdf_links
        metadata['total_documentos'] = len(pdf_links)
        metadata['data_extracao'] = time.strftime("%Y-%m-%d %H:%M:%S")
        
    except Exception as e:
        print(f"[AVISO] Erro ao extrair metadados: {e}")
    
    return metadata

def create_leilao_folder(metadata, base_path="leiloes"):
    """Cria pasta para o leilão baseada nos metadados."""
    try:
        # Criar nome da pasta limpo
        codigo = metadata.get('codigo_zuk', 'sem_codigo')
        endereco = metadata.get('endereco_completo', metadata.get('bairro', 'sem_endereco'))
        
        # Limpar caracteres especiais
        endereco_limpo = re.sub(r'[^\w\s-]', '', endereco)
        endereco_limpo = re.sub(r'\s+', '_', endereco_limpo.strip())[:50]
        
        folder_name = f"leilao_{codigo}_{endereco_limpo}"
        folder_path = os.path.join(base_path, folder_name)
        
        os.makedirs(folder_path, exist_ok=True)
        return folder_path
        
    except Exception as e:
        print(f"[ERRO] Erro ao criar pasta: {e}")
        # Pasta padrão se der erro
        folder_path = os.path.join(base_path, f"leilao_{int(time.time())}")
        os.makedirs(folder_path, exist_ok=True)
        return folder_path

def download_pdf(url, folder_path, filename=None):
    """Baixa um arquivo PDF para a pasta especificada."""
    try:
        if not filename:
            filename = os.path.basename(urlparse(url).path)
            if not filename.endswith('.pdf'):
                filename = f"documento_{int(time.time())}.pdf"
        
        file_path = os.path.join(folder_path, filename)
        
        # Evitar download duplicado
        if os.path.exists(file_path):
            print(f"[INFO] PDF já existe: {filename}")
            return file_path
        
        # Headers para simular navegador
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36'
        }
        
        response = requests.get(url, stream=True, headers=headers, timeout=30)
        response.raise_for_status()
        
        with open(file_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        print(f"[SUCESSO] PDF baixado: {filename}")
        return file_path
        
    except Exception as e:
        print(f"[ERRO] Erro ao baixar PDF {url}: {e}")
        return None

def save_metadata(metadata, folder_path):
    """Salva metadados em arquivo JSON."""
    try:
        metadata_path = os.path.join(folder_path, "metadata.json")
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
        print(f"[SUCESSO] Metadados salvos em: {metadata_path}")
    except Exception as e:
        print(f"[ERRO] Erro ao salvar metadados: {e}")


def save_html_page(driver, filename):
    """Salva o HTML da página atual em um arquivo."""
    try:
        html_content = driver.page_source
        os.makedirs("html_pages", exist_ok=True)
        file_path = os.path.join("html_pages", filename)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"[SUCESSO] HTML salvo em: {file_path}")
        return file_path
    except Exception as e:
        print(f"[ERRO] Erro ao salvar HTML: {e}")
        return None


def iterate_cards_by_links(driver):
    """Coleta todos os links primeiro, depois navega um por um."""
    processed_count = 0
    page_count = 1
    
    while True:
        print(f"\n[INFO] === Processando página {page_count} ===")
        
        # Aguardar carregamento da página
        time.sleep(3)
        
        # Encontrar cards na página atual
        cards = driver.find_elements(By.CLASS_NAME, "card-property")
        
        if not cards:
            print("[INFO] Nenhum card encontrado na página atual.")
            break
        
        # Coletar todos os links da página atual
        card_links = []
        for card in cards:
            try:
                link = card.find_element(By.TAG_NAME, "a").get_attribute("href")
                if link:
                    card_links.append(link)
            except:
                pass
        
        print(f"[INFO] Encontrados {len(card_links)} imóveis na página {page_count}")
        
        # Processar cada link da página atual
        for i, link in enumerate(card_links):
            processed_count += 1
            print(f"\n[INFO] Processando imóvel {processed_count} (Página {page_count}, Item {i + 1}/{len(card_links)})")
            print(f"[INFO] URL: {link}")
            
            driver.get(link)
            time.sleep(4)  # Aguardar carregamento completo da página do imóvel
            
            # Extrair metadados
            metadata = extract_property_metadata(driver)
            
            # Criar pasta para o leilão
            folder_path = create_leilao_folder(metadata)
            
            # Salvar metadados
            save_metadata(metadata, folder_path)
            
            # Salvar HTML da página do imóvel na pasta do leilão
            html_filename = f"pagina_imovel.html"
            html_path = os.path.join(folder_path, html_filename)
            try:
                with open(html_path, 'w', encoding='utf-8') as f:
                    f.write(driver.page_source)
                print(f"[SUCESSO] HTML salvo: {html_filename}")
            except Exception as e:
                print(f"[ERRO] Erro ao salvar HTML: {e}")
            
            # Baixar PDFs
            for j, pdf_info in enumerate(metadata.get('documentos_pdf', [])):
                safe_label = re.sub(r'[^\w\s-]', '', pdf_info['label'])
                safe_label = re.sub(r'\s+', '_', safe_label.strip())
                filename = f"{j+1:02d}_{safe_label}.pdf"
                download_pdf(pdf_info['url'], folder_path, filename)
                time.sleep(1)  # Pequena pausa entre downloads
            
            print(f"[SUCESSO] Leilão {processed_count} processado. Pasta: {folder_path}")
            print(f"[INFO] Metadados: Código {metadata.get('codigo_zuk')}, Preço R$ {metadata.get('preco')}")
            
            # Voltar para a lista
            driver.back()
            time.sleep(2)  # Aguardar retorno à lista
            close_modal(driver)
            time.sleep(1)
            
            # Pausa entre imóveis para não sobrecarregar o servidor
            time.sleep(2)
        
        # Tentar carregar mais leilões
        print(f"\n[INFO] Tentando carregar mais leilões...")
        try:
            # Scroll até o botão para garantir que está visível
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            
            # Procurar o botão "Carregar Mais"
            load_more_button = driver.find_element(By.ID, "btn_carregarMais")
            
            # Verificar se o botão está visível e clicável
            if load_more_button.is_displayed() and load_more_button.is_enabled():
                print("[INFO] Clicando no botão 'Carregar Mais'...")
                
                # Usar JavaScript para clicar (mais confiável)
                driver.execute_script("arguments[0].click();", load_more_button)
                
                # Aguardar carregamento dos novos itens
                time.sleep(5)
                
                # Verificar se novos cards foram carregados
                new_cards = driver.find_elements(By.CLASS_NAME, "card-property")
                if len(new_cards) > len(cards):
                    print(f"[SUCESSO] Novos leilões carregados. Total atual: {len(new_cards)}")
                    page_count += 1
                    continue
                else:
                    print("[INFO] Nenhum novo leilão foi carregado.")
                    break
            else:
                print("[INFO] Botão 'Carregar Mais' não está disponível.")
                break
                
        except Exception as e:
            print(f"[INFO] Não foi possível carregar mais leilões: {e}")
            print("[INFO] Provavelmente chegamos ao final da lista.")
            break
    
    print(f"\n[SUCESSO] Processamento concluído! Total de imóveis processados: {processed_count}")
    return processed_count


def main():
    # Configurar navegador (sem headless para ver as ações)
    options = webdriver.ChromeOptions()
    # Adicionar argumentos para evitar detecção
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    
    # Remover propriedade webdriver para evitar detecção
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

    try:
        print("[INFO] Iniciando scraping do Portal Zuk...")
        start_time = time.time()
        
        # 1. Abrir a página
        open_zukpage(driver)
        
        # 2. Processar todos os leilões (com paginação)
        total_processed = iterate_cards_by_links(driver)
        
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"\n[RELATÓRIO FINAL]")
        print(f"Total de imóveis processados: {total_processed}")
        print(f"Tempo total de execução: {duration:.2f} segundos ({duration/60:.2f} minutos)")
        print(f"Média por imóvel: {duration/total_processed:.2f} segundos" if total_processed > 0 else "N/A")

    except Exception as e:
        print(f"[ERRO] Ocorreu um erro: {e}")

    finally:
        driver.quit()
        print("[INFO] Navegador fechado.")
        print("[INFO] Scraping finalizado!")

if __name__ == "__main__":
    main()
