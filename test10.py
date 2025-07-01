import google.generativeai as genai
import streamlit as st
from streamlit_chat import message
import streamlit.components.v1 as components
from prometheus_client import Counter, Histogram, generate_latest, REGISTRY
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading

genai.configure(api_key="AIzaSyArTog-quWD9Tqf-CkkFAq_-UOZfK1FTtA")

st.set_page_config(page_title="Deloitte Angola AI - Seu Assistente Virtual", page_icon="📈")

# --- Informações da Deloitte Angola (Integradas) ---
deloitte_info = {
    "nome_empresa": "Deloitte Angola",
    "localizacao": "Luanda, Angola",
    "endereco_fisico": "Condomínio Cidade Financeira, Via S8, Bloco 4 - 5º, Talatona, Luanda, Angola",
    "telefone_geral": "+244 923 xxx xxx", # Telefone encontrado online
    "site": "https://www.deloitte.com/africa-lusofona/pt.html", # Site da Deloitte África Lusófona, que inclui Angola
    "servicos_principais": [
        "Auditoria e Asseguração",
        "Consultoria (Gestão, Estratégia, Tecnologia)",
        "Consultoria Fiscal e Jurídica",
        "Risk Advisory (Gestão de Risco)",
        "Financial Advisory (Consultoria Financeira)",
        "Serviços de Outsourcing (BPS - Business Process Solutions, RH e Payroll)",
        "Serviços de Cibersegurança (Cyber Defense & Resilience, Cyber Operate, Cyber Strategy & Transformation, Digital Trust & Privacy, Enterprise Security)",
        "Inteligência Artificial Generativa (através do Centro de Excelência em IA Generativa)",
        "Assessoria em Transações e Reestruturações",
        "Serviços para Setor Público",
        "Serviços para Indústria de Energia, Recursos e Manufatura",
        "Serviços para Setor Financeiro"
    ],
    "foco_mercado": "Grandes empresas, grupos económicos, instituições públicas e privadas em Angola",
    "recrutamento_foco": "Profissionais com formação superior em Economia, Gestão, Contabilidade e Fiscalidade.",
    "projetos_sociais": "PACT Fund (apoia projetos sociais em Angola nas áreas de educação, empregabilidade, empreendedorismo e sustentabilidade ambiental)."
}

@st.cache_resource
def initialize_metrics():
    request_count = Counter('app_requests_total', 'Total number of requests to the app')
    response_latency = Histogram('app_response_latency_seconds', 'Response latency in seconds')
    agent_interaction_count = Counter('agent_interactions_total', 'Total number of interactions with the sales agent')
    return request_count, response_latency, agent_interaction_count

REQUEST_COUNT, RESPONSE_LATENCY, AGENT_INTERACTION_COUNT = initialize_metrics()

def agente_deloitte(pergunta_usuario, historico_conversa, deloitte_conhecimento=deloitte_info):
    """
    Agente para responder perguntas sobre a Deloitte Angola, lembrando do histórico da conversa.
    """
    start_time = time.time()
    model_deloitte = genai.GenerativeModel('gemini-2.0-flash-exp')

    prompt_deloitte = f"""Você é um agente de atendimento ao cliente da {deloitte_conhecimento['nome_empresa']} em {deloitte_conhecimento['localizacao']}. Você deve responder perguntas com base nas seguintes informações:\n\n"""
    prompt_deloitte += f"- **Sobre a Deloitte Angola:** Somos uma das maiores empresas de serviços profissionais do mundo, com uma forte presença em Angola. Nosso endereço é {deloitte_conhecimento['endereco_fisico']} e nosso telefone geral é {deloitte_conhecimento['telefone_geral']}. Você pode encontrar mais informações em nosso site: {deloitte_conhecimento['site']}.\n"
    prompt_deloitte += f"- **Nossos Serviços Principais:** Oferecemos uma ampla gama de serviços para grandes empresas, grupos económicos e instituições públicas e privadas. Nossos serviços incluem: {', '.join(deloitte_conhecimento['servicos_principais'])}.\n"
    prompt_deloitte += f"- **Foco no Mercado:** A Deloitte Angola colabora com os principais grupos económicos e empresas angolanas em diversos projetos estratégicos e operacionais.\n"
    prompt_deloitte += f"- **Inovação e Tecnologia:** Recentemente, lançamos um Centro de Excelência em Inteligência Artificial Generativa no ANGOTIC 2025 para impulsionar a transformação digital e desenvolver soluções baseadas em IA.\n"
    prompt_deloitte += f"- **Recrutamento:** Buscamos constantemente talentos, especialmente jovens com formação superior em Economia, Gestão, Contabilidade e Fiscalidade, com ambição e capacidade de trabalhar em equipa.\n"
    prompt_deloitte += f"- **Responsabilidade Social:** Através do nosso PACT Fund, apoiamos projetos sociais em Angola, com foco em educação, empregabilidade, empreendedorismo e sustentabilidade ambiental.\n"
    prompt_deloitte += "Seu nome é Deloitte AI. Seja amigável, profissional e utilize um tom formal e informativo, adequado a uma empresa de consultoria e auditoria de grande porte."

    # Adiciona o histórico da conversa ao prompt
    prompt_deloitte += "\nHistórico da Conversa:\n"
    for turno in historico_conversa:
        prompt_deloitte += f"{'Usuário' if turno['is_user'] else 'Deloitte AI'}: {turno['content']}\n"

    prompt_deloitte += f"""\nCom base nas informações acima e no histórico da conversa, responda à seguinte pergunta do usuário da melhor forma possível:\n\n"{pergunta_usuario}"\n\nSe a pergunta for feita em português, responda somente em português. Se for em inglês, responda em inglês. Tente lembrar de informações ditas anteriormente na conversa para fornecer respostas mais contextuais, evita dizer sempre 'Olá' diga somente uma vez, e das outras vezes comece com outras frases que se adpta a pergunta do usuário."""

    response_deloitte = model_deloitte.generate_content(prompt_deloitte)
    latency = time.time() - start_time
    RESPONSE_LATENCY.observe(latency)
    AGENT_INTERACTION_COUNT.inc()
    return response_deloitte.text

# --- Interface Streamlit Aprimorada e Mais Atraente com Memória ---
st.markdown(
    """
    <style>
        .stChatInputContainer {
            position: fixed;
            bottom: 0;
            background-color: #0e1117; /* Cor de fundo escura */
            padding: 16px;
            border-top: 1px solid #2c303a; /* Borda mais escura */
        }
        .streamlit-expander header:first-child {
            font-size: 16px;
            font-weight: bold;
            color: #f8f9fa; /* Texto claro */
        }
        .user-message {
            background-color: #1e3a8a !important; /* Azul mais escuro */
            color: #f8f9fa !important;
            border-radius: 8px;
            padding: 8px 12px;
            margin-bottom: 8px;
            width: fit-content;
            float: right;
            clear: both;
        }
        .agent-message {
            background-color: #38a169 !important; /* Verde mais escuro */
            color: #f8f9fa !important;
            border-radius: 8px;
            padding: 8px 12px;
            margin-bottom: 8px;
            width: fit-content;
            float: left;
            clear: both;
        }
        .stApp {
            background-color: #0e1117; /* Cor de fundo escura para toda a app */
            color: #f8f9fa; /* Cor do texto padrão clara */
        }
        .sidebar .sidebar-content {
            padding-top: 1rem;
            background-color: #1a202c; /* Sidebar mais escura */
            color: #f8f9fa;
        }
        .sidebar-subheader {
            font-size: 14px;
            font-weight: bold;
            margin-top: 10px;
            color: #cbd5e0; /* Subheader mais claro */
        }
        .sidebar-item {
            font-size: 12px;
            margin-bottom: 5px;
            color: #e2e8f0; /* Item da sidebar mais claro */
        }
        .stTextInput>div>div>input {
            color: #f8f9fa;
            background-color: #2d3748; /* Input mais escuro */
            border-color: #4a5568;
        }
        .stTextArea>div>div>textarea {
            color: #f8f9fa;
            background-color: #2d3748; /* Textarea mais escuro */
            border-color: #4a5568;
        }
        .stButton>button {
            color: #f8f9fa;
            background-color: #4299e1; /* Botão azul mais claro */
            border-color: #4299e1;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("Deloitte AI - Seu Assistente Virtual 📈")
st.markdown("Olá! 👋 Como posso te ajudar hoje com informações sobre a Deloitte Angola?")

# Inicializa o histórico de mensagens
if "messages" not in st.session_state:
    st.session_state["messages"] = []

# Exibe o histórico de mensagens com estilos personalizados
for msg in st.session_state["messages"]:
    if msg["is_user"]:
        st.markdown(f'<div class="user-message"><i class="fa fa-user-circle"></i> {msg["content"]}</div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="agent-message"><i class="fa fa-robot"></i> {msg["content"]}</div>', unsafe_allow_html=True)

# Caixa de entrada para o usuário
if prompt := st.chat_input("Digite sua pergunta aqui..."):
    REQUEST_COUNT.inc()
    st.session_state["messages"].append({"content": prompt, "is_user": True})
    st.markdown(f'<div class="user-message"><i class="fa fa-user-circle"></i> {prompt}</div>', unsafe_allow_html=True)

    # Obtém a resposta do agente, passando o histórico da conversa
    resposta_do_agente = agente_deloitte(prompt, st.session_state["messages"])
    st.session_state["messages"].append({"content": resposta_do_agente, "is_user": False})
    st.markdown(f'<div class="agent-message"><i class="fa fa-robot"></i> {resposta_do_agente}</div>', unsafe_allow_html=True)

# Barra Lateral com visual aprimorado
with st.sidebar:
    st.header("Informações Deloitte Angola")
    with st.expander("**Sobre Nós**", expanded=False):
        st.markdown(f"<p class='sidebar-item'>Localização: {deloitte_info['localizacao']}</p>", unsafe_allow_html=True)
        st.markdown(f"<p class='sidebar-item'>Endereço: {deloitte_info['endereco_fisico']}</p>", unsafe_allow_html=True)
        st.markdown(f"<p class='sidebar-item'>Telefone: {deloitte_info['telefone_geral']}</p>", unsafe_allow_html=True)
        st.markdown(f"<p class='sidebar-item'>Site: <a href='{deloitte_info['site']}' target='_blank'>{deloitte_info['site']}</a></p>", unsafe_allow_html=True)
    with st.expander("**Serviços**", expanded=False):
        for service in deloitte_info['servicos_principais']:
            st.markdown(f"<p class='sidebar-item'>- {service}</p>", unsafe_allow_html=True)
    with st.expander("**Foco e Recrutamento**", expanded=False):
        st.markdown(f"<p class='sidebar-item'>Foco de Mercado: {deloitte_info['foco_mercado']}</p>", unsafe_allow_html=True)
        st.markdown(f"<p class='sidebar-item'>Recrutamento: {deloitte_info['recrutamento_foco']}</p>", unsafe_allow_html=True)
    with st.expander("**Inovação e Responsabilidade Social**", expanded=False):
        st.markdown(f"<p class='sidebar-item'>Inovação: Centro de Excelência em IA Generativa</p>", unsafe_allow_html=True)
        st.markdown(f"<p class='sidebar-item'>Projetos Sociais: {deloitte_info['projetos_sociais']}</p>", unsafe_allow_html=True)
    st.markdown("---")
    st.markdown("Deloitte Angola: Impactando o que importa.")

# Adiciona a biblioteca Font Awesome para os ícones
components.html(
    """
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" integrity="sha512-9usAa10IRO0HhonpyAIVpjrylPvoDwiPUiKdWk5t3PyolY1cOd4DSE0Ga+ri4AuTroPR5aQvXU9xC6qOPnzFeg==" crossorigin="anonymous" referrerpolicy="no-referrer" />
    """,
    height=0,
)

# Exponha as métricas em uma rota HTTP
class MetricsHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/metrics':
            self.send_response(200)
            self.send_header('Content-Type', 'text/plain; charset=utf-8')
            self.end_headers()
            self.wfile.write(generate_latest(REGISTRY))
        else:
            self.send_response(404)
            self.end_headers()

def run_metrics_server(port=8000):
    httpd = HTTPServer(('0.0.0.0', port), MetricsHandler)
    httpd.serve_forever()

if __name__ == '__main__':
    metrics_thread = threading.Thread(target=run_metrics_server)
    metrics_thread.daemon = True
    metrics_thread.start()
    # O loop principal do Streamlit continua rodando aqui
