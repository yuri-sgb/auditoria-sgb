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

st.set_page_config(page_title="SGB Audit Hub v5", layout="wide", page_icon="🛡️")

# CSS para melhorar a visualização
st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stTextArea textarea { font-size: 14px !important; }
    .justificado { 
        text-align: justify; 
        border: 2px solid #004587; 
        padding: 25px; 
        background-color: #ffffff; 
        color: #1f1f1f;
        font-family: 'Arial', sans-serif;
    }
    .highlight { color: #004587; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

def extrair_texto_pdf(file):
    if file is None: return ""
    try:
        pdf = PyPDF2.PdfReader(file)
        return " ".join([page.extract_text() for page in pdf.pages])
    except:
        return ""

def capturar_metadados_ata(texto):
    uasg = re.search(r"(?:UASG|Unidade Gestora)[:\s]*(\d{6})", texto, re.I)
    gestor = re.search(r"(?:Gestor|Responsável)[:\s]*([A-Z\s]{5,40})", texto, re.I)
    prazo = re.search(r"(\d+)\s*(?:dias|mês|meses)\s*(?:para entrega|de entrega)", texto, re.I)
    u_cod = uasg.group(1) if uasg else None
    return {
        "UASG": u_cod if u_cod else "Não Identificado",
        "Unidade": UASG_MAP.get(u_cod, "Não identificada no cabeçalho"),
        "Gestor": gestor.group(1).strip() if gestor else "A DEFINIR",
        "Prazo": f"{prazo.group(1)} dias" if prazo else "30 dias"
    }

def buscar_marca_na_proposta(texto):
    """Busca cirúrgica de Marca/Modelo apenas na Proposta"""
    # Procura padrões comuns em propostas comerciais de fornecedores
    padroes = [
        r"(?:Marca|Fabricante)[:\s]+([A-Z0-9\s\.\-\/]+)",
        r"(?:Modelo|Referência)[:\s]+([A-Z0-9\s\.\-\/]+)",
        r"MARCA\/MODELO[:\s]+([A-Z0-9\s\.\-\/]+)"
    ]
    
    resultados = []
    for p in padroes:
        match = re.search(p, texto, re.I)
        if match:
            val = match.group(1).strip().split('\n')[0]
            if len(val) > 2: resultados.append(val)
    
    return " / ".join(list(dict.fromkeys(resultados))) if resultados else ""

st.title("🛡️ SGB Audit & Design Hub")
st.markdown("---")

# Inicialização de estados
if 'marca_auto' not in st.session_state: st.session_state['marca_auto'] = ""
if 'meta_ata' not in st.session_state: st.session_state['meta_ata'] = {}

# --- SEÇÃO 1: UPLOAD E TRIANGULAÇÃO ---
st.header("📂 1. Documentação e Auditoria")
col_f1, col_f2, col_f3 = st.columns(3)

with col_f1: f_tr = st.file_uploader("1. Termo de Referência (TR)", type='pdf')
with col_f2: f_prop = st.file_uploader("2. Proposta de Preços (Fonte de Marca/Modelo)", type='pdf')
with col_f3: f_ata = st.file_uploader("3. Ata de Registro de Preços (Cabeçalho)", type='pdf')

if st.button("🔍 Realizar Leitura e Triangulação Automática"):
    if f_prop and f_ata:
        texto_prop = extrair_texto_pdf(f_prop)
        texto_ata = extrair_texto_pdf(f_ata)
        
        # Ação 1: Buscar Marca EXCLUSIVAMENTE na proposta
        st.session_state['marca_auto'] = buscar_marca_na_proposta(texto_prop)
        
        # Ação 2: Capturar Metadados na ATA
        st.session_state['meta_ata'] = capturar_metadados_ata(texto_ata)
        
        st.success("Análise concluída com sucesso!")
    else:
        st.error("Obrigatório carregar ao menos a Proposta e a ATA para extração.")

# Exibição de Metadados se existirem
if st.session_state['meta_ata']:
    m = st.session_state['meta_ata']
    st.markdown("#### 📌 Dados Capturados da ATA")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("UASG", m['UASG'])
    c2.metric("Unidade", m['Unidade'])
    c3.metric("Gestor", m['Gestor'])
    c4.metric("Prazo", m['Prazo'])

st.markdown("---")

# --- SEÇÃO 2: SANEAMENTO ---
st.header("✍️ 2. Saneamento e Transposição para o SEI")

col_edit, col_res = st.columns([1, 1])

with col_edit:
    txt_original = st.text_area("Descrição Original (Copie do documento):", height=200)
    
    # Campo de Marca preenchido automaticamente pela busca na Proposta
    marca_final = st.text_input("Marca/Modelo (Extraído automaticamente da Proposta):", 
                                value=st.session_state['marca_auto'],
                                help="Este campo é preenchido automaticamente com dados da Proposta de Preços.")
    
    if not st.session_state['marca_auto'] and f_prop:
        st.caption("⚠️ Não detectamos a marca automaticamente no PDF. Por favor, digite manualmente.")

with col_res:
    if st.button("🪄 Gerar Versão Final Saneada"):
        termos_erro = ["similar", "equivalente", "referência", "qualidade superior"]
        
        if any(t in txt_original.lower() for t in termos_erro):
            st.error("🛑 ERRO DE CONFORMIDADE: Descrição contém termos proibidos ('similar', 'referência', etc).")
        elif not marca_final:
            st.warning("⚠️ Informe a Marca/Modelo para finalizar o texto.")
        else:
            st.markdown("**Texto Final (Justificado - Pronto para o SEI):**")
            # Aplicação das regras de saneamento: CAIXA ALTA, troca de ; por .
            saneado = txt_original.upper().replace(";", ".")
            
            output = f"""<div class="justificado">
                {saneado}<br><br>
                <b>MARCA/FABRICANTE: {marca_final}</b>
            </div>"""
            st.markdown(output, unsafe_allow_html=True)
            st.button("📋 Copiar Texto (Simulação)")

st.sidebar.markdown("### Instruções")
st.sidebar.write("1. Suba os PDFs.\n2. O sistema busca a Marca na Proposta.\n3. O sistema busca o Gestor e UASG na ATA.\n4. Corrija o texto e use na transposição.")
