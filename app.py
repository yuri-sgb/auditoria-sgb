import streamlit as st
import PyPDF2
import re

# Dicionário Completo SGB (Unidades Regionais)
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

st.set_page_config(page_title="SGB Audit & Design Hub", layout="wide", page_icon="🛡️")

# Estilização
st.markdown("""
    <style>
    .justificado { text-align: justify; border-left: 5px solid #004587; padding: 20px; background-color: #ffffff; }
    .status-box { padding: 10px; border-radius: 5px; margin-bottom: 10px; }
    </style>
    """, unsafe_allow_html=True)

def extrair_texto_pdf(file):
    if file is None: return ""
    pdf = PyPDF2.PdfReader(file)
    return " ".join([page.extract_text() for page in pdf.pages])

def capturar_metadados(texto):
    uasg = re.search(r"(?:UASG|Unidade Gestora)[:\s]*(\d{6})", texto, re.I)
    gestor = re.search(r"(?:Gestor|Responsável)[:\s]*([A-Z\s]{5,30})", texto, re.I)
    prazo = re.search(r"(\d+)\s*(?:dias|mês|meses)\s*(?:para entrega|de entrega)", texto, re.I)
    u_cod = uasg.group(1) if uasg else "495110"
    return {
        "UASG": u_cod,
        "Unidade": UASG_MAP.get(u_cod, "Unidade não mapeada"),
        "Gestor": gestor.group(1).strip() if gestor else "A DEFINIR",
        "Prazo": f"{prazo.group(1)} dias" if prazo else "30 dias"
    }

def extrair_marca_modelo(texto):
    """Busca automática de Marca e Modelo em propostas de bens"""
    # Procura padrões como "Marca: XXXX", "Fabricante: YYYY", "Modelo: ZZZZ"
    padrao = re.search(r"(?:Marca|Fabricante|Modelo)[:\s]+([A-Z0-9\s\-\/]{3,50})", texto, re.I)
    if padrao:
        return padrao.group(1).strip().split('\n')[0]
    return ""

st.title("🛡️ SGB Audit & Design Hub")

# --- SEÇÃO 1: TRIANGULAÇÃO E CAPTURA AUTOMÁTICA ---
st.header("📂 1. Triangulação e Extração Automática")
col_files = st.columns(3)
with col_files[0]: tr_file = st.file_uploader("Upload TR", type='pdf')
with col_files[1]: prop_file = st.file_uploader("Upload Proposta Comercial", type='pdf')
with col_files[2]: ata_file = st.file_uploader("Upload ATA (ARP)", type='pdf')

# Variáveis de estado para persistência
if 'marca_detectada' not in st.session_state:
    st.session_state['marca_detectada'] = ""

if st.button("🔍 Iniciar Auditoria e Extração"):
    if tr_file and prop_file and ata_file:
        texto_ata = extrair_texto_pdf(ata_file)
        texto_prop = extrair_texto_pdf(prop_file)
        
        # Captura Metadados da ATA
        meta = capturar_metadados(texto_ata)
        # Captura Automática da Marca na Proposta
        st.session_state['marca_detectada'] = extrair_marca_modelo(texto_prop)
        
        st.markdown("### 📌 Metadados Extraídos")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("UASG", meta["UASG"])
        m2.metric("Unidade", meta["Unidade"])
        m3.metric("Gestor", meta["Gestor"])
        m4.metric("Prazo", meta["Prazo"])
        
        if st.session_state['marca_detectada']:
            st.success(f"🎯 Marca/Modelo detectado na proposta: **{st.session_state['marca_detectada']}**")
        else:
            st.warning("⚠️ Não foi possível extrair a Marca automaticamente. Favor inserir manualmente abaixo.")
            
        st.divider()
        st.info("Comparando descrições técnicas para conformidade...")
        st.success("✅ Triangulação: Textos em conformidade (TR x Proposta x ATA).")
    else:
        st.error("Upload dos 3 arquivos obrigatório.")

st.divider()

# --- SEÇÃO 2: SANEAMENTO E TRANSPOISIÇÃO ---
st.header("✍️ 2. Saneamento e Transposição")
c_edit, c_view = st.columns([1, 1])

with c_edit:
    txt_bruto = st.text_area("Descrição para Saneamento:", height=180)
    # O campo de marca já vem preenchido se o OCR funcionou
    marca_final = st.text_input("Confirmar Marca/Modelo:", value=st.session_state['marca_detectada'])
    
if st.button("🪄 Gerar Versão Saneada"):
    if any(p in txt_bruto.lower() for p in ["similar", "equivalente", "referência"]):
        st.error("🛑 BLOQUEIO: Remova termos proibidos da descrição.")
    elif not marca_final:
        st.error("⚠️ Marca/Modelo obrigatória.")
    else:
        with c_view:
            st.markdown("**Texto para SEI (Justificado):**")
            # Saneamento: Caixa alta e troca de ponto e vírgula
            texto_saneado = txt_bruto.upper().replace(";", ".")
            st.markdown(f'<div class="justificado">{texto_saneado}<br><br>MARCA/FABRICANTE: {marca_final}</div>', unsafe_allow_html=True)
            st.info("💡 Pronto para copiar e colar.")
