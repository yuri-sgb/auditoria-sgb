import streamlit as st
import PyPDF2
import re

# Dicionário de UASGs SGB
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

st.set_page_config(page_title="Atualização das Atas", layout="wide", page_icon="🛡️")

# Funções de Extração Inteligente
def extrair_texto(file):
    try:
        reader = PyPDF2.PdfReader(file)
        return "\n".join([page.extract_text() for page in reader.pages])
    except:
        return ""

def extrair_especificacao(texto):
    """Tenta localizar o bloco de descrição técnica (Geralmente após 'Objeto' ou 'Item')"""
    # Procura por padrões onde a descrição costuma começar
    padrao = re.search(r"(?i)(?:Descrição|Especificação|Objeto)[:\-]*\s*(.*)", texto, re.DOTALL)
    if padrao:
        # Pega os primeiros 1000 caracteres para não sobrecarregar
        return padrao.group(1).strip()[:1000]
    return ""

def localizar_uasg(texto):
    match = re.search(r"495\d{3}", texto)
    return match.group(0) if match else None

def localizar_marca(texto):
    padroes = [r"(?i)Marca\s*[:\-]*\s*([^\n,;]+)", r"(?i)Fabricante\s*[:\-]*\s*([^\n,;]+)"]
    for p in padroes:
        m = re.search(p, texto)
        if m: return m.group(1).strip().upper()
    return ""

# Inicialização do Estado (Session State)
if 'texto_extraido' not in st.session_state: st.session_state.texto_extraido = ""
if 'marca_extraida' not in st.session_state: st.session_state.marca_extraida = ""
if 'uasg_extraida' not in st.session_state: st.session_state.uasg_extraida = "Não identificado"

st.title("🛡️ SGB Audit & Design Hub - Gold Edition")

# --- ÁREA DE UPLOAD ---
st.header("1. Carga de Documentos")
col_f1, col_f2, col_f3 = st.columns(3)
with col_f1: f_tr = st.file_uploader("Termo de Referência", type='pdf')
with col_f2: f_prop = st.file_uploader("Proposta (Fonte de Dados)", type='pdf')
with col_f3: f_ata = st.file_uploader("Ata de Registro de Preços", type='pdf')

if st.button("🔍 Extrair Dados e Alimentar Saneador"):
    if f_prop and f_ata:
        t_prop = extrair_texto(f_prop)
        t_ata = extrair_texto(f_ata)
        
        # Alimenta os estados do sistema
        st.session_state.texto_extraido = extrair_especificacao(t_prop) if t_prop else extrair_especificacao(t_ata)
        st.session_state.marca_extraida = localizar_marca(t_prop)
        uasg_cod = localizar_uasg(t_ata)
        st.session_state.uasg_extraida = f"{uasg_cod} - {UASG_MAP.get(uasg_cod, '')}"
        
        st.success("Dados extraídos! Verifique os campos abaixo.")
    else:
        st.error("Carregue os arquivos para extração automática.")

st.divider()

# --- ÁREA DE SANEAMENTO ---
st.header("✍️ 2. Saneamento e Versão Final")

c1, c2 = st.columns(2)

with c1:
    st.subheader("Entrada de Dados")
    # Este campo é alimentado automaticamente, mas permite edição manual livre
    desc_para_editar = st.text_area(
        "Redação Original (Editável):", 
        value=st.session_state.texto_extraido, 
        height=250,
        help="O sistema tentou extrair o texto dos PDFs. Você pode apagar e colar o que quiser aqui."
    )
    
    marca_final = st.text_input("Confirmar Marca/Modelo:", value=st.session_state.marca_extraida)
    st.caption(f"UASG Identificada: {st.session_state.uasg_extraida}")

with c2:
    st.subheader("Resultado para o SEI")
    if st.button("🪄 Gerar Texto Saneado"):
        # Validação de Termos Proibidos
        if any(p in desc_para_editar.lower() for p in ["similar", "equivalente", "referencia"]):
            st.error("🛑 BLOQUEIO: Remova termos como 'similar' ou 'equivalente' da descrição técnica.")
        elif not marca_final:
            st.warning("⚠️ Forneça a Marca/Modelo para concluir o saneamento.")
        else:
            # Regras de Ouro: Caixa Alta, troca de ; por .
            saneado = desc_para_editar.upper().replace(";", ".")
            
            st.markdown("**Versão Final (Cumpra o Saneamento):**")
            texto_final_formatado = f"{saneado}\n\nMARCA/FABRICANTE: {marca_final.upper()}"
            
            st.code(texto_final_formatado, language="text")
            st.success("Copiado para a área de transferência? (Use o botão acima)")
            
            # Placeholder para a Imagem
            st.divider()
            st.markdown("🖼️ **Representação Visual Sugerida:**")
            st.image("https://via.placeholder.com/400x200.png?text=Preview+Item+Logo+SGB", caption="O layout seguirá o manual SGB 2026")

st.sidebar.info("Dica: Se o texto extraído vier com muitos erros de espaçamento, você pode corrigi-los manualmente na caixa de edição antes de gerar a versão final.")
