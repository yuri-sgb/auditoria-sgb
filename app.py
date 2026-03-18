import streamlit as st
import PyPDF2
import re
from PIL import Image, ImageDraw, ImageFont
import io

# Configurações de Identidade
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

st.set_page_config(page_title="Ajuste na Descrição do Objeto - ATA", layout="wide")

# --- FUNÇÕES TÉCNICAS ---
def extrair_texto(file):
    try:
        reader = PyPDF2.PdfReader(file)
        return "\n".join([p.extract_text() for p in reader.pages])
    except: return ""

def formatar_especificacao(texto):
    # Limpeza de ruídos de tabelas
    ruidos = ["ITEM", "DESCRIÇÃO", "QTDE", "UF", "PREÇO", "UNITARIO", "TOTAL", "R\$", "UNITÁRIO"]
    for r in ruidos:
        texto = re.sub(rf"(?i){r}", "", texto)
    
    # Busca o bloco do Kit (baseado no seu PDF)
    match = re.search(r"(Kit de Microcistina.*?(?:Substrato|Solução \"STOP\").*?)\n", texto, re.S | re.I)
    if match:
        bloco = match.group(1).strip()
        # Quebra de linha em listas numeradas
        bloco = re.sub(r"(\d+\s+(?:Frasco|Tubo|Kit|Manual))", r"\n\1", bloco)
        return bloco
    return texto[:800]

def buscar_detalhes(texto):
    res = {"fabricante": "", "modelo": "", "procedencia": ""}
    m_fab = re.search(r"(?i)Fabricante\s*[:\-]*\s*([^\n]+)", texto)
    m_mod = re.search(r"(?i)Modelo\s*[:\-]*\s*([^\n]+)", texto)
    m_pro = re.search(r"(?i)Procedência\s*[:\-]*\s*([^\n]+)", texto)
    
    if m_fab: res["fabricante"] = m_fab.group(1).strip().upper()
    if m_mod: res["modelo"] = m_mod.group(1).strip().upper()
    if m_pro: res["procedencia"] = m_pro.group(1).strip().upper()
    return res

def gerar_imagem_tecnica(texto_final):
    # Cria uma imagem em branco (A4 proporção ou card)
    img = Image.new('RGB', (800, 600), color=(255, 255, 255))
    d = ImageDraw.Draw(img)
    
    # Tenta carregar uma fonte padrão, se falhar usa a básica
    try:
        fnt = ImageFont.load_default()
    except:
        fnt = ImageFont.load_default()

    # Desenha uma borda azul (SGB Style)
    d.rectangle([10, 10, 790, 590], outline=(0, 69, 135), width=3)
    d.text((30, 30), "SGB - SERVIÇO GEOLÓGICO DO BRASIL", fill=(0, 69, 135))
    d.text((30, 60), "ESPECIFICAÇÃO TÉCNICA SANEADA", fill=(0, 0, 0))
    
    # Insere o texto (limitado para caber no card)
    corpo_texto = texto_final[:1000]
    d.multiline_text((30, 100), corpo_texto, fill=(50, 50, 50), spacing=4)
    
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()

# --- INTERFACE ---
st.title("🛡️ Ajuste na Descrição do Objeto - ATA")

if 'store' not in st.session_state:
    st.session_state.store = {"txt": "", "detalhes": {}, "resultado": ""}

st.header("1. Insira os seguintes documentos para análise")
c1, c2, c3 = st.columns(3)
with c1: f_tr = st.file_uploader("Termo de Referência", type='pdf')
with c2: f_prop = st.file_uploader("Proposta de Preços", type='pdf')
with c3: f_ata = st.file_uploader("Ata de Registro", type='pdf')

if st.button("🔍 ANALISAR DOCUMENTOS"):
    if f_prop:
        t = extrair_texto(f_prop)
        st.session_state.store["txt"] = formatar_especificacao(t)
        st.session_state.store["detalhes"] = buscar_detalhes(t)
        
        uasg_m = re.search(r"495\d{3}", t)
        if uasg_m:
            st.info(f"UASG: {uasg_m.group(0)} - {UASG_MAP.get(uasg_m.group(0), 'UNIDADE REGIONAL')}")
        st.success("Análise concluída!")

st.divider()

st.header("2. Descrição Ajustada")
col_in, col_out = st.columns(2)

with col_in:
    txt_edit = st.text_area("Redação para Ajuste:", value=st.session_state.store["txt"], height=350)
    det = st.session_state.store["detalhes"]
    f_fab = st.text_input("Fabricante:", value=det.get("fabricante", ""))
    f_mod = st.text_input("Modelo:", value=det.get("modelo", ""))
    f_pro = st.text_input("Procedência:", value=det.get("procedencia", ""))

with col_out:
    if st.button("🪄 GERAR DESCRIÇÃO FINAL"):
        # Aplica Saneamento
        final = txt_edit.upper().replace(";", ".")
        bloco_final = f"{final}\n\nFABRICANTE: {f_fab.upper()}\nMODELO: {f_mod.upper()}\nPROCEDÊNCIA: {f_pro.upper()}"
        st.session_state.store["resultado"] = bloco_final

    if st.session_state.store["resultado"]:
        st.code(st.session_state.store["resultado"], language="text")
        
        # Módulo de Imagem
        st.subheader("🖼️ Geração de Imagem do Item")
        img_data = gerar_imagem_tecnica(st.session_state.store["resultado"])
        st.image(img_data, caption="Visualização Técnica Saneada")
        
        st.download_button(
            label="📥 Download da Imagem (.PNG)",
            data=img_data,
            file_name="descricao_saneada_sgb.png",
            mime="image/png"
        )
