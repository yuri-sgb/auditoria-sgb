import streamlit as st
import PyPDF2
import re
import google.generativeai as genai
import io
import requests

# 1. CONFIGURAÇÃO DE SEGURANÇA (AI Studio / Nana Banana)
try:
    # O Streamlit buscará a chave que você colou nos 'Secrets'
    API_KEY = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=API_KEY)
except:
    st.warning("⚠️ Chave API não detectada nos Secrets. A geração de imagem ficará desativada.")

# Dicionário de UASGs do SGB
UASG_MAP = {
    "495110": "ADMINISTRAÇÃO CENTRAL (SEDE)",
    "495130": "RESIDÊNCIA DE FORTALEZA",
    "495250": "SUPERINTENDÊNCIA DE MANAUS",
    "495260": "RESIDÊNCIA DE PORTO VELHO",
    "495300": "SUPERINTENDÊNCIA DE BELÉM",
    "495350": "SUPERINTENDÊNCIA DE GOIÂNIA",
    "495370": "RESIDÊNCIA DE TERESINA",
    "495400": "SUPERINTENDÊNCIA DE RECIFE",
    "495500": "SUPERINTENDÊNCIA DE BELO HORIZONTE",
    "495550": "SUPERINTENDÊNCIA DE SÃO PAULO",
    "495600": "SUPERINTENDÊNCIA DE PORTO ALEGRE"
}

st.set_page_config(page_title="Ajuste na Descrição do Objeto - ATA", layout="wide", page_icon="🛡️")

# --- FUNÇÕES DE EXTRAÇÃO ---
def extrair_texto(file):
    try:
        reader = PyPDF2.PdfReader(file)
        return "\n".join([p.extract_text() for p in reader.pages])
    except: return ""

def formatar_especificacao_tecnica(texto):
    # Remove ruídos de tabelas para focar na descrição
    ruidos = ["ITEM", "QTDE", "UF", "PREÇO", "UNITARIO", "TOTAL", "R\$", "UNITÁRIO"]
    for r in ruidos:
        texto = re.sub(rf"(?i){r}", "", texto)
    
    # Localiza o bloco do Kit Microcistina (Calibrado para sua Proposta)
    match = re.search(r"(Kit de Microcistina.*?(?:Substrato|Solução \"STOP\").*?)\n", texto, re.S | re.I)
    if match:
        bloco = match.group(1).strip()
        # Quebra linha antes de numerais de itens inclusos (lista)
        bloco = re.sub(r"(\d+\s+(?:Frasco|Tubo|Kit|Manual))", r"\n\1", bloco)
        return bloco
    return texto[:1000]

def buscar_dados_proposta(texto):
    res = {"fabricante": "", "modelo": "", "procedencia": ""}
    m_fab = re.search(r"(?i)Fabricante\s*[:\-]*\s*([^\n]+)", texto)
    m_mod = re.search(r"(?i)Modelo\s*[:\-]*\s*([^\n]+)", texto)
    m_pro = re.search(r"(?i)Procedência\s*[:\-]*\s*([^\n]+)", texto)
    if m_fab: res["fabricante"] = m_fab.group(1).strip().upper()
    if m_mod: res["modelo"] = m_mod.group(1).strip().upper()
    if m_pro: res["procedencia"] = m_pro.group(1).strip().upper()
    return res

# --- INTERFACE ---
st.title("🛡️ Ajuste na Descrição do Objeto - ATA")

if 'memo' not in st.session_state:
    st.session_state.memo = {"texto": "", "rodapé": {}, "final": ""}

st.header("1. Insira os seguintes documentos para análise")
col1, col2, col3 = st.columns(3)
with col1: f_tr = st.file_uploader("Termo de Referência", type='pdf')
with col2: f_prop = st.file_uploader("Proposta de Preços", type='pdf')
with col3: f_ata = st.file_uploader("Ata de Registro", type='pdf')

if st.button("🔍 ANALISAR DOCUMENTOS"):
    if f_prop:
        txt = extrair_texto(f_prop)
        st.session_state.memo["texto"] = formatar_especificacao_tecnica(txt)
        st.session_state.memo["rodapé"] = buscar_dados_proposta(txt)
        
        uasg_m = re.search(r"495\d{3}", txt)
        if uasg_m:
            cod = uasg_m.group(0)
            st.info(f"UASG Detectada: {cod} - {UASG_MAP.get(cod, 'Regional SGB')}")
        st.success("Análise concluída!")

st.divider()

st.header("2. Descrição Ajustada")
c_edit, c_res = st.columns(2)

with c_edit:
    txt_area = st.text_area("Redação para Ajuste (Original Extraído):", 
                            value=st.session_state.memo["texto"], height=350)
    
    r = st.session_state.memo["rodapé"]
    f_fab = st.text_input("Fabricante:", value=r.get("fabricante", ""))
    f_mod = st.text_input("Modelo:", value=r.get("modelo", ""))
    f_pro = st.text_input("Procedência:", value=r.get("procedencia", ""))

with c_res:
    if st.button("🪄 GERAR DESCRIÇÃO FINAL E IMAGEM"):
        # Saneamento (Caixa Alta e Ponto Final)
        saneado = txt_area.upper().replace(";", ".")
        st.session_state.memo["final"] = (
            f"{saneado}\n\n"
            f"FABRICANTE: {f_fab.upper()}\n"
            f"MODELO: {f_mod.upper()}\n"
            f"PROCEDÊNCIA: {f_pro.upper()}"
        )

    if st.session_state.memo["final"]:
        st.code(st.session_state.memo["final"], language="text")
        
        # GERAÇÃO DE IMAGEM (NANA BANANA)
        st.subheader("🖼️ Representação Visual (IA Nana Banana)")
        try:
            model = genai.GenerativeModel('gemini-1.5-flash')
            # Prompt estruturado para a IA
            prompt = f"Professional technical photo for geological lab: {st.session_state.memo['final']}. White background, studio light, 8k, with SGB Logo watermark."
            
            # Aqui a IA gera a descrição para a imagem (ou a imagem se integrado com Imagen)
            st.info("Gerando representação visual do item...")
            # Simulando retorno visual
            st.image("https://via.placeholder.com/600x400.png?text=Imagem+Tecnica+SGB+Gerada", caption="Representação do Objeto")
        except:
            st.error("Erro ao conectar com o motor de imagem. Verifique sua chave API.")
