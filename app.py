import streamlit as st
import PyPDF2
import re

# Dicionário Completo SGB
UASG_MAP = {
    "495110": "Administração Central (Sede)",
    "495130": "Residência de Fortaleza",
    "495250": "Superintendência de Manaus",
    "495260": "Residência de Porto Velho",
    "495300": "Superintendência de Belém",
    "495350": "Superintendência de Goiânia",
    "495370": "Residência de Teresina",
    "495400": "Superintendência de Recife",
    "495500": "Superintendência de Belo Horizonte",
    "495550": "Superintendência de São Paulo",
    "495600": "Superintendência de Porto Alegre"
}

st.set_page_config(page_title="SGB Audit Hub v6", layout="wide")

# Funções de Extração
def extrair_texto(file):
    try:
        reader = PyPDF2.PdfReader(file)
        full_text = ""
        for page in reader.pages:
            full_text += page.extract_text() + "\n"
        return full_text
    except:
        return ""

def localizar_uasg(texto):
    # Procura por 6 dígitos que iniciem com 495 (padrão SGB)
    match = re.search(r"495\d{3}", texto)
    return match.group(0) if match else None

def localizar_marca_proposta(texto):
    # Busca por padrões de marcas em propostas de produtos
    padroes = [
        r"(?i)Marca\s*[:\-]*\s*([^\n\r,;]+)",
        r"(?i)Fabricante\s*[:\-]*\s*([^\n\r,;]+)",
        r"(?i)Modelo\s*[:\-]*\s*([^\n\r,;]+)"
    ]
    for p in padroes:
        m = re.search(p, texto)
        if m:
            return m.group(1).strip().upper()
    return ""

st.title("🛡️ SGB Audit & Design Hub - V6.0")

# Inicialização de estados para evitar perda de dados ao clicar
if 'dados' not in st.session_state:
    st.session_state.dados = {"uasg": "", "unidade": "", "marca": "", "texto_final": ""}

# --- UPLOADS ---
col1, col2, col3 = st.columns(3)
with col1: f_tr = st.file_uploader("1. Termo de Referência", type='pdf')
with col2: f_prop = st.file_uploader("2. Proposta (Marca/Modelo)", type='pdf')
with col3: f_ata = st.file_uploader("3. Ata (UASG/Gestor)", type='pdf')

if st.button("🔍 EXECUTAR AUDITORIA"):
    if f_prop and f_ata:
        t_prop = extrair_texto(f_prop)
        t_ata = extrair_texto(f_ata)
        
        # Identificar UASG e Unidade
        uasg_cod = localizar_uasg(t_ata) or localizar_uasg(t_prop)
        st.session_state.dados["uasg"] = uasg_cod or "Não Encontrado"
        st.session_state.dados["unidade"] = UASG_MAP.get(uasg_cod, "Unidade não identificada")
        
        # Identificar Marca na Proposta
        st.session_state.dados["marca"] = localizar_marca_proposta(t_prop)
        st.success("Análise de arquivos concluída!")
    else:
        st.error("Carregue a Proposta e a Ata para análise.")

# --- EXIBIÇÃO DE DADOS ---
st.markdown("### 📌 Resultados da Extração")
c1, c2, c3 = st.columns(3)
with c1: st.metric("UASG Detectada", st.session_state.dados["uasg"])
with c2: st.metric("Unidade Regional", st.session_state.dados["unidade"])
with c3: 
    # Permite edição manual caso a extração falhe
    st.session_state.dados["marca"] = st.text_input("Marca/Modelo (Verifique na Proposta):", value=st.session_state.dados["marca"])

st.divider()

# --- SANEAMENTO ---
st.header("✍️ Saneamento de Texto")
texto_bruto = st.text_area("Cole a descrição original aqui:", height=150)

if st.button("🪄 GERAR TEXTO SANEADO"):
    if any(p in texto_bruto.lower() for p in ["similar", "equivalente", "referencia"]):
        st.error("🛑 BLOQUEIO: O texto contém termos proibidos. Use a descrição exata da proposta.")
    elif not st.session_state.dados["marca"]:
        st.warning("⚠️ Informe a Marca/Modelo para concluir.")
    else:
        # Regras de transposição: Caixa alta, ponto no lugar de ponto e vírgula
        saneado = texto_bruto.upper().replace(";", ".")
        marca_f = st.session_state.dados["marca"].upper()
        
        resultado = f"{saneado}\n\nMARCA/FABRICANTE: {marca_f}"
        st.session_state.dados["texto_final"] = resultado

if st.session_state.dados["texto_final"]:
    st.markdown("#### ✅ Texto Final (Justificado para o SEI)")
    st.code(st.session_state.dados["texto_final"], language="text")
    st.info("Copie o texto acima e cole no seu documento oficial.")
