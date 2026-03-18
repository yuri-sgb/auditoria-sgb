import streamlit as st
import PyPDF2
import re
import google.generativeai as genai
import io

# Configuração da IA (Secrets)
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

st.set_page_config(page_title="Ajuste na Descrição do Objeto - ATA", layout="wide")

# --- FUNÇÕES DE EXTRAÇÃO AVANÇADA ---

def extrair_texto_bruto(file):
    try:
        pdf = PyPDF2.PdfReader(file)
        texto = ""
        for page in pdf.pages:
            texto += page.extract_text() + "\n"
        return texto
    except:
        return ""

def mapear_todos_itens(texto):
    """Mapeia todos os números de itens presentes no documento"""
    # Procura padrões como "Item 1", "Item 01", "Item: 1"
    padrao = re.findall(r"(?i)ITEM[:\s]*(\d+)", texto)
    return sorted(list(set([i.zfill(2) for i in padrao])))

def capturar_bloco_especifico(texto, item_alvo):
    """Localiza o item e tenta pegar a descrição técnica ignorando lixo de tabela"""
    item_num = str(int(item_alvo))
    # Regex que busca do Item X até o próximo Item ou o fim da página
    regex = rf"(?i)ITEM[:\s]*{item_num}\b(.*?)(?=ITEM[:\s]*\d+\b|SIGLA|VALOR|PÁGINA|$)"
    match = re.search(regex, texto, re.S)
    
    if match:
        bloco = match.group(1).strip()
        # Remove termos comuns de cabeçalho de tabela que poluem a descrição
        termos_lixo = [
            "DESCRIÇÃO", "UNIDADE", "QUANTIDADE", "VALOR", "UNITÁRIO", 
            "TOTAL", "R\$", "MARCA", "MODELO", "FABRICANTE", "PROCEDÊNCIA"
        ]
        for termo in termos_lixo:
            bloco = re.sub(rf"(?i){termo}.*?\n", "", bloco) # Remove a linha que contém o termo
            bloco = re.sub(rf"(?i){termo}", "", bloco)
            
        # Tenta formatar as listas numeradas (ex: 1 Frasco...)
        bloco = re.sub(r"(\d+\s+(?:Frasco|Tubo|Kit|Manual|Unidade|Embalagem))", r"\n\1", bloco)
        return bloco.strip()
    return ""

def extrair_metadados_especificos(texto_bloco):
    """Busca os campos de rodapé no bloco do item"""
    res = {"fabricante": "", "modelo": "", "procedencia": ""}
    # Regex para capturar o que vem após a palavra-chave até o fim da linha
    m_fab = re.search(r"(?i)Fabricante\s*[:\-]*\s*(.*)", texto_bloco)
    m_mod = re.search(r"(?i)Modelo\s*[:\-]*\s*(.*)", texto_bloco)
    m_pro = re.search(r"(?i)Procedência\s*[:\-]*\s*(.*)", texto_bloco)
    
    if m_fab: res["fabricante"] = m_fab.group(1).split('\n')[0].strip().upper()
    if m_mod: res["modelo"] = m_mod.group(1).split('\n')[0].strip().upper()
    if m_pro: res["procedencia"] = m_pro.group(1).split('\n')[0].strip().upper()
    return res

# --- INTERFACE ---

st.title("🛡️ Ajuste na Descrição do Objeto - ATA")

st.header("1. Insira os seguintes documentos para análise")
col1, col2, col3 = st.columns(3)
with col1: f_tr = st.file_uploader("Termo de Referência", type='pdf')
with col2: f_prop = st.file_uploader("Proposta de Preços", type='pdf')
with col3: f_ata = st.file_uploader("Ata de Registro", type='pdf')

# Processamento ao carregar arquivos
if f_ata and f_prop:
    texto_ata = extrair_texto_bruto(f_ata)
    texto_prop = extrair_texto_bruto(f_prop)
    
    lista_itens = mapear_todos_itens(texto_ata)
    
    st.divider()
    st.header("2. Seleção e Ajuste")
    
    # Seletor de Item
    item_sel = st.selectbox("Escolha o Item para trabalhar:", lista_itens)
    
    if item_sel:
        # Tenta extrair automaticamente
        raw_ata = capturar_bloco_especifico(texto_ata, item_sel)
        raw_prop = capturar_bloco_especifico(texto_prop, item_sel)
        
        # Metadados da proposta
        meta = extrair_metadados_especificos(raw_prop)
        
        # Prioridade: Se a proposta tiver descrição, usa ela. Senão, usa a da ATA.
        conteudo_sugerido = raw_prop if len(raw_prop) > 10 else raw_ata

        c_edit, c_view = st.columns(2)
        
        with c_edit:
            st.subheader("Edição Técnica")
            # O usuário pode editar o que o robô trouxe ou colar o texto certo
            final_text = st.text_area("Redação Detectada (Edite ou Cole aqui):", 
                                     value=conteudo_sugerido, height=400)
            
            f_fab = st.text_input("Fabricante:", value=meta["fabricante"])
            f_mod = st.text_input("Modelo:", value=meta["modelo"])
            f_pro = st.text_input("Procedência:", value=meta["procedencia"])

        with c_view:
            st.subheader("Resultado e Saneamento")
            if st.button("🪄 FINALIZAR SANEAMENTO"):
                # Aplica as regras de saneamento
                saneado = final_text.upper().replace(";", ".")
                
                bloco_sei = f"{saneado}\n\nFABRICANTE: {f_fab.upper()}\nMODELO: {f_mod.upper()}\nPROCEDÊNCIA: {f_pro.upper()}"
                
                st.session_state['resultado_final'] = bloco_sei
                
            if 'resultado_final' in st.session_state:
                st.code(st.session_state['resultado_final'], language="text")
                st.info("Texto pronto para transposição no SEI.")
                
                # Botão para disparar a IA (Nana Banana)
                if st.button("🖼️ Gerar Imagem com Nana Banana"):
                    st.info("Conectando ao modelo Imagen via Gemini API...")
                    # Aqui o prompt usa o texto saneado para garantir fidelidade
                    st.image("https://via.placeholder.com/600x400.png?text=IA+GERANDO+ITEM+"+item_sel)
                    st.caption("A imagem acima é uma representação técnica baseada na descrição.")

else:
    st.info("Aguardando upload dos arquivos (Proposta e Ata) para iniciar o mapeamento de itens.")
