import google.generativeai as genai
import streamlit as st
from streamlit_chat import message
import streamlit.components.v1 as components
from prometheus_client import Counter, Histogram, generate_latest, REGISTRY
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading

genai.configure(api_key="AIzaSyArTog-quWD9Tqf-CkkFAq_-UOZfK1FTtA")

st.set_page_config(page_title="Xtendo Ai - Seu Assistente Virtual", page_icon="🤖")

# --- Dados Fictícios da Xtendo Group (Integrados) ---
xtendo_info = {
    "nome_empresa": "Xtendo Group",
    "localizacao": "Luanda, Angola",
    "delivery_horario": "10h às 23h todos os dias",
    "delivery_area": "toda a cidade de Luanda e arredores",
    "delivery_taxa": "500 AOA (pode variar)",
    "pagamentos_delivery": "Transferência bancária, Multicaixa e pagamento na entrega (dinheiro)",
    "rastreamento_pedido": "Link enviado por SMS ou e-mail",
    "suporte_delivery": "Chat ou telefone +244 9XXXXXXX",
    "restaurantes_parceiros": ["Sabor Angolano", "Pizza Place", "Delícias do Mar"],
    "ecommerce_produtos": "eletrônicos, moda e itens para casa",
    "ecommerce_frete_luanda": "Padrão (3-5 dias úteis), Expresso (1-2 dias úteis)",
    "ecommerce_troca_devolucao": "7 dias após o recebimento (produto original)",
    "ecommerce_pagamentos": "Multicaixa, transferência bancária e cartões de crédito internacionais",
    "ecommerce_suporte": "suporte@xtendogroup.ao ou chat online",
    "logistica_servicos": "transporte de pequenas e médias cargas em Luanda e algumas rotas intermunicipais",
    "logistica_prazo_luanda": "1-2 dias úteis",
    "logistica_contato": "Formulário online ou telefone",
    "telefone_geral": "+244 9XXXXXXX",
    "endereco_fisico": "Rua da República, nº 123, Luanda",
    "site": "www.xtendogroup.ao"
}

@st.cache_resource
def initialize_metrics():
    request_count = Counter('app_requests_total', 'Total number of requests to the app')
    response_latency = Histogram('app_response_latency_seconds', 'Response latency in seconds')
    agent_interaction_count = Counter('agent_interactions_total', 'Total number of interactions with the sales agent')
    return request_count, response_latency, agent_interaction_count

REQUEST_COUNT, RESPONSE_LATENCY, AGENT_INTERACTION_COUNT = initialize_metrics()

def agente_de_vendas_xtendo(pergunta_usuario, historico_conversa, xtendo_conhecimento=xtendo_info):
    """
    Agente para responder perguntas sobre a Xtendo Group, lembrando do histórico da conversa.
    """
    start_time = time.time()
    model_vendas = genai.GenerativeModel('gemini-2.0-flash-exp')

    prompt_xtendo = f"""Você é um agente de atendimento ao cliente da {xtendo_conhecimento['nome_empresa']} em {xtendo_conhecimento['localizacao']}. Você deve responder perguntas com base nas seguintes informações:\n\n"""
    prompt_xtendo += f"- **Delivery:** Atendemos em {xtendo_conhecimento['delivery_area']}, das {xtendo_conhecimento['delivery_horario']}. Taxa de entrega: {xtendo_conhecimento['delivery_taxa']}. Pagamentos: {xtendo_conhecimento['pagamentos_delivery']}. Rastreamento: {xtendo_conhecimento['rastreamento_pedido']}. Suporte: {xtendo_conhecimento['suporte_delivery']}. Restaurantes parceiros: {', '.join(xtendo_conhecimento['restaurantes_parceiros'])}.\n"
    prompt_xtendo += f"- **E-commerce:** Vendemos {xtendo_conhecimento['ecommerce_produtos']}. Frete em Luanda: {xtendo_conhecimento['ecommerce_frete_luanda']}. Troca/Devolução: {xtendo_conhecimento['ecommerce_troca_devolucao']}. Pagamentos: {xtendo_conhecimento['ecommerce_pagamentos']}. Suporte: {xtendo_conhecimento['ecommerce_suporte']}.\n"
    prompt_xtendo += f"- **Logística:** Oferecemos {xtendo_conhecimento['logistica_servicos']}. Prazo em Luanda: {xtendo_conhecimento['logistica_prazo_luanda']}. Contato para orçamento: {xtendo_conhecimento['logistica_contato']}.\n"
    prompt_xtendo += f"- **Informações Gerais:** Telefone: {xtendo_conhecimento['telefone_geral']}. Endereço: {xtendo_conhecimento['endereco_fisico']}. Site: {xtendo_conhecimento['site']}.\n"
    prompt_xtendo += "Seu nome é Xtendo Ai. Seja amigável e profissional."

    # Adiciona o histórico da conversa ao prompt
    prompt_xtendo += "\nHistórico da Conversa:\n"
    for turno in historico_conversa:
        prompt_xtendo += f"{'Usuário' if turno['is_user'] else 'Xtendo Ai'}: {turno['content']}\n"

    prompt_xtendo += f"""\nCom base nas informações acima e no histórico da conversa, responda à seguinte pergunta do usuário da melhor forma possível:\n\n"{pergunta_usuario}"\n\nSe a pergunta for feita em português, responda somente em português. Se for em inglês, responda em inglês. Tente lembrar de informações ditas anteriormente na conversa para fornecer respostas mais contextuais, evita dizer sempre 'Olá' diga somente uma vez, e das outras vezes comece com outras frases que se adpta a pergunta do usuário."""

    response_xtendo = model_vendas.generate_content(prompt_xtendo)
    latency = time.time() - start_time
    RESPONSE_LATENCY.observe(latency)
    AGENT_INTERACTION_COUNT.inc()
    return response_xtendo.text

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

st.title("Xtendo AI - Seu Assistente Virtual 🤖")
st.markdown("Olá! 👋 Como posso te ajudar hoje?")

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
    resposta_do_agente = agente_de_vendas_xtendo(prompt, st.session_state["messages"])
    st.session_state["messages"].append({"content": resposta_do_agente, "is_user": False})
    st.markdown(f'<div class="agent-message"><i class="fa fa-robot"></i> {resposta_do_agente}</div>', unsafe_allow_html=True)

# Barra Lateral com visual aprimorado
with st.sidebar:
    st.header("Informações Xtendo Group")
    with st.expander("**Sobre Nós**", expanded=False):
        st.markdown(f"<p class='sidebar-item'>Localização: {xtendo_info['localizacao']}</p>", unsafe_allow_html=True)
        st.markdown(f"<p class='sidebar-item'>Telefone: {xtendo_info['telefone_geral']}</p>", unsafe_allow_html=True)
        st.markdown(f"<p class='sidebar-item'>Site: <a href='{xtendo_info['site']}' target='_blank'>{xtendo_info['site']}</a></p>", unsafe_allow_html=True)
    with st.expander("**Delivery**", expanded=False):
        st.markdown(f"<p class='sidebar-item'>Horário: {xtendo_info['delivery_horario']}</p>", unsafe_allow_html=True)
        st.markdown(f"<p class='sidebar-item'>Área de Cobertura: {xtendo_info['delivery_area']}</p>", unsafe_allow_html=True)
        st.markdown(f"<p class='sidebar-item'>Taxa de Entrega: {xtendo_info['delivery_taxa']}</p>", unsafe_allow_html=True)
        st.markdown(f"<p class='sidebar-item'>Pagamentos: {xtendo_info['pagamentos_delivery']}</p>", unsafe_allow_html=True)
    with st.expander("**E-commerce**", expanded=False):
        st.markdown(f"<p class='sidebar-item'>Produtos: {xtendo_info['ecommerce_produtos']}</p>", unsafe_allow_html=True)
        st.markdown(f"<p class='sidebar-item'>Frete (Luanda): {xtendo_info['ecommerce_frete_luanda']}</p>", unsafe_allow_html=True)
        st.markdown(f"<p class='sidebar-item'>Troca/Devolução: {xtendo_info['ecommerce_troca_devolucao']}</p>", unsafe_allow_html=True)
        st.markdown(f"<p class='sidebar-item'>Pagamentos: {xtendo_info['ecommerce_pagamentos']}</p>", unsafe_allow_html=True)
    with st.expander("**Logística**", expanded=False):
        st.markdown(f"<p class='sidebar-item'>Serviços: {xtendo_info['logistica_servicos']}</p>", unsafe_allow_html=True)
        st.markdown(f"<p class='sidebar-item'>Prazo (Luanda): {xtendo_info['logistica_prazo_luanda']}</p>", unsafe_allow_html=True)
        st.markdown(f"<p class='sidebar-item'>Contato: {xtendo_info['logistica_contato']}</p>", unsafe_allow_html=True)
    st.markdown("---")
    st.markdown("Xtendo Group Mais Perto De Si🤝")

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