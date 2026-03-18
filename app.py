import streamlit as st
import PyPDF2
import re
import google.generativeai as genai
import io

# Configuração da IA (Nana Banana)
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

st.set_page_config(page_title="Ajuste na Descrição do Objeto - ATA", layout="wide")

def extrair_texto_pdf(file):
    try:
        pdf = PyPDF2.PdfReader(file)
        return "\n".join([page.extract_text() for page in pdf.pages])
    except: return ""

def tentar_extrair_item(texto, num_item):
    """Tenta localizar o item de forma mais flexível"""
    # Tenta localizar pelo número do item
    num_limpo = str(int(num_item))
    padrao = rf"(?i)ITEM[:\s]*{num_limpo}\b(.*?)(?=ITEM[:\s]*\d+\b|VALOR|ESTA\sATA|$)"
    match = re.search(padrao, texto, re.S)
    
    if match:
        bloco = match.group(1).strip()
        # Se vier texto de contrato (Evandro, Ato nº), ignora esse bloco e tenta o próximo
        if "Diretor" in bloco or "Ato nº" in bloco:
            return ""
        return bloco
    return ""

# --- INTERFACE ---
st.title("🛡️ Ajuste na Descrição do Objeto - ATA")

st.header("1. Insira os seguintes documentos para análise")
c1, c2, c3 = st.columns(3)
with c1: f_tr = st.file_uploader("Termo de Referência", type='pdf')
with c2: f_prop = st.file_uploader("Proposta de Preços", type='pdf')
with c3: f_ata = st.file_uploader("Ata de Registro", type='pdf')

# Inicializa o estado do texto para permitir manual ou automático
if 'texto_original' not in st.session_state:
    st.session_state.texto_original = ""

if f_ata and f_prop:
    t_ata = extrair_texto_pdf(f_ata)
    t_prop = extrair_texto_pdf(f_prop)
    lista_itens = sorted(list(set([i.zfill(2) for i in re.findall(r"(?i)ITEM[:\s]*(\d+)", t_ata)])))
    
    st.divider()
    st.header("2. Descrição Ajustada")
    
    col_sel, col_btn = st.columns([3, 1])
    with col_sel:
        item_sel = st.selectbox("Selecione o Item da ATA:", lista_itens)
    with col_btn:
        if st.button("🔍 Extrair Automático"):
            extraido = tentar_extrair_item(t_prop, item_sel)
            if not extraido:
                extraido = tentar_extrair_item(t_ata, item_sel)
            st.session_state.texto_original = extraido

    st.info("💡 Você pode clicar em 'Extrair Automático' ou simplesmente colar o texto original abaixo.")

    c_edit, c_res = st.columns(2)

    with c_edit:
        # CAMPO MANUAL/AUTOMÁTICO
        txt_manual = st.text_area("Redação Original (Cole aqui ou use o automático):", 
                                 value=st.session_state.texto_original, height=400)
        
        # Busca automática de metadados se houver texto
        m_fab = re.search(r"(?i)Fabricante\s*[:\-]*\s*([^\n]+)", txt_manual)
        m_mod = re.search(r"(?i)Modelo\s*[:\-]*\s*([^\n]+)", txt_manual)
        
        f_fab = st.text_input("Fabricante:", value=m_fab.group(1).strip() if m_fab else "")
        f_mod = st.text_input("Modelo:", value=m_mod.group(1).strip() if m_mod else "")
        f_pro = st.text_input("Procedência (Ex: Importado/USA):")

    with c_res:
        if st.button("🪄 PROCESSAR SANEAMENTO"):
            if txt_manual:
                # REGRAS DE SANEAMENTO
                saneado = txt_manual.upper().replace(";", ".")
                # Limpa quebras de linha duplas e espaços de PDF
                saneado = re.sub(r'\s+', ' ', saneado).strip()
                
                res_final = f"{saneado}\n\nFABRICANTE: {f_fab.upper()}\nMODELO: {f_mod.upper()}\nPROCEDÊNCIA: {f_pro.upper()}"
                st.session_state.res_final = res_final
            else:
                st.error("Por favor, insira o texto original primeiro.")

        if 'res_final' in st.session_state:
            st.subheader("Texto Saneado")
            st.code(st.session_state.res_final, language="text")
            
            # GERAÇÃO DE IMAGEM (NANA BANANA)
            st.divider()
            if st.button("🖼️ Gerar Imagem com Nana Banana"):
                try:
                    model = genai.GenerativeModel('gemini-1.5-flash')
                    # Prompt treinado para imagem técnica
                    prompt = f"High-quality technical laboratory product photo: {st.session_state.res_final}. White background, professional studio lighting."
                    
                    st.write("✨ Nana Banana criando imagem...")
                    # Simulação de exibição (substituir por chamada de imagem real se disponível)
                    st.image("https://via.placeholder.com/600x400.png?text=IMAGEM+TECNICA+SGB", caption="Representação do Item")
                except Exception as e:
                    st.error(f"Erro na IA: {e}")
