import streamlit as st
import PyPDF2
import re
import os
import io
from PIL import Image

# --- CONFIGURAÇÃO DE AMBIENTE (Simulação da API Imagen) ---
# Em produção, estas chaves seriam configuradas no Streamlit Cloud Secrets
# os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "caminho/para/seu/keyfile.json"
# import google.generativeai as genai
# genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
# model_imagen = genai.GenerativeModel('imagen-3')

# Dicionário de UASGs SGB
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

# --- FUNÇÕES TÉCNICAS (OCR e Regex) ---
def extrair_texto_pdf(file):
    try:
        reader = PyPDF2.PdfReader(file)
        return "\n".join([page.extract_text() for page in reader.pages])
    except: return ""

def formatar_especificacao_microcistina(texto):
    """Extrai e quebra linhas do seu exemplo específico de Kit"""
    # Remove lixo de tabela
    texto = re.sub(r"(?i)ITEM|QTDE|UF|PREÇO|UNITARIO|TOTAL|R\$", "", texto)
    # Busca o bloco do Kit
    match = re.search(r"(Kit de Microcistina.*?(?:Solução \"Stop\"|Substrato).*?)\n", texto, re.S | re.I)
    if match:
        bloco = match.group(1).strip()
        # Quebra linha antes de numerais de itens inclusos
        bloco = re.sub(r"(\d+\s+(?:Frasco|Tubo|Kit|Manual))", r"\n\1", bloco)
        return bloco
    return texto[:1000]

def buscar_detalhes_proposta(texto):
    """Busca cirúrgica na proposta"""
    res = {"fabricante": "", "modelo": "", "procedencia": ""}
    m_fab = re.search(r"(?i)Fabricante\s*[:\-]*\s*([^\n,;]+)", texto)
    m_mod = re.search(r"(?i)Modelo\s*[:\-]*\s*([^\n,;]+)", texto)
    m_pro = re.search(r"(?i)Procedência\s*[:\-]*\s*([^\n,;]+)", texto)
    if m_fab: res["fabricante"] = m_fab.group(1).strip().upper()
    if m_mod: res["modelo"] = m_mod.group(1).strip().upper()
    if m_pro: res["procedencia"] = m_pro.group(1).strip().upper()
    return res

# --- MÓDULO DE GERAÇÃO DE IMAGEM (IA Generativa) ---
def gerar_imagem_ia_sgb(prompt_saneado):
    """
    Simulação da chamada à API Imagen.
    Em produção, este prompt seria enviado para:
    response = model_imagen.generate_images(prompt=prompt_final)
    """
    st.info("Chamando motor de IA Generativa (Imagen)...")
    
    # Construção do Prompt Técnico para a IA (conforme treinado)
    prompt_final = (
        f"A high-definition, professional studio product photograph of: {prompt_saneado}. "
        "The image must feature a subtle official SGB (Serviço Geológico do Brasil) "
        "logomarca 2026 watermark in the bottom right corner. Isolated on a clean "
        "white background with soft technical lighting. Ultra-detailed texture."
    )
    
    # Placeholder: Em produção, retornaríamos os bytes reais da imagem gerada.
    # img_bytes = response.images[0].bytes
    
    # Para teste, vamos carregar uma imagem placeholder
    return "https://via.placeholder.com/800x600.png?text=IMAGEM+GERADA+PELA+IA+COM+LOGO+SGB"

# --- INTERFACE ---
st.title("🛡️ Ajuste na Descrição do Objeto - ATA")
st.markdown("---")

# Inicialização de Estados
if 'store' not in st.session_state:
    st.session_state.store = {"txt_orig": "", "det": {}, "final": "", "img_bytes": None}

# --- SEÇÃO 1: UPLOAD ---
st.header("1. Insira os seguintes documentos para análise")
c1, c2, c3 = st.columns(3)
with c1: f_tr = st.file_uploader("1. Termo de Referência", type='pdf')
with c2: f_prop = st.file_uploader("2. Proposta de Preços (Fonte de Dados)", type='pdf')
with c3: f_ata = st.file_uploader("3. Ata de Registro", type='pdf')

if st.button("🔍 ANALISAR DOCUMENTOS E EXTRAIR DADOS"):
    if f_prop and f_ata:
        t_prop = extrair_texto_pdf(f_prop)
        t_ata = extrair_texto_pdf(f_ata)
        
        # Mapeamento UASG
        uasg_m = re.search(r"495\d{3}", t_ata)
        if uasg_m:
            cod = uasg_m.group(0)
            st.info(f"UASG: {cod} - {UASG_MAP.get(cod, 'UNIDADE REGIONAL')}")
            
        # Alimenta Estados
        st.session_state.store["txt_orig"] = formatar_especificacao_microcistina(t_prop)
        st.session_state.store["det"] = buscar_detalhes_proposta(t_prop)
        st.success("Análise concluída!")
    else:
        st.error("Upload da Proposta e da Ata é obrigatório.")

st.markdown("---")

# --- SEÇÃO 2: AJUSTE E IMAGEM ---
st.header("2. Descrição Ajustada")
col_in, col_out = st.columns(2)

with col_in:
    # Campo de texto alimentado automaticamente, mas editável
    txt_edit = st.text_area("Redação para Ajuste (Original):", 
                            value=st.session_state.store["txt_orig"], height=350)
    
    det = st.session_state.store["det"]
    f_fab = st.text_input("Fabricante (da Proposta):", value=det.get("fabricante", ""))
    f_mod = st.text_input("Modelo (da Proposta):", value=det.get("modelo", ""))
    f_pro = st.text_input("Procedência:", value=det.get("procedencia", ""))

with col_out:
    if st.button("🪄 GERAR DESCRIÇÃO FINAL E IMAGEM TÉCNICA"):
        # Aplica Saneamento Técnico
        saneado = txt_edit.upper().replace(";", ".")
        bloco_final = (
            f"{saneado}\n\n"
            f"FABRICANTE: {f_fab.upper()}\n"
            f"MODELO: {f_mod.upper()}\n"
            f"PROCEDÊNCIA: {f_pro.upper()}"
        )
        st.session_state.store["final"] = bloco_final
        
        # Chamada ao Motor de Geração de Imagem
        # st.session_state.store["img_bytes"] = gerar_imagem_ia_sgb(bloco_final)
        
    if st.session_state.store["final"]:
        st.code(st.session_state.store["final"], language="text")
        st.success("Copiado para a área de transferência? (Use o botão acima)")
        
        # Exibição da Imagem Gerada pela IA
        st.divider()
        st.subheader("🖼️ Representação Visual Gerada (IA Imagen)")
        
        # Simulação da exibição da imagem (Em produção, carregaríamos os bytes)
        st.image("https://via.placeholder.com/600x400.png?text=IMAGEM+GERADA+PELA+IA+COM+LOGO+SGB", caption="Item Gerado com Identidade Visual SGB 2026")
        
        # Botão de Download da Imagem Real
        st.download_button(
            label="📥 Download da Imagem (.PNG)",
            data=io.BytesIO().getvalue(), # Placeholder
            file_name="item_saneado_sgb.png",
            mime="image/png"
        )
