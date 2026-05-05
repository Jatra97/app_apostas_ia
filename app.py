import streamlit as st
import requests
import google.generativeai as genai

# 1. Configuração das APIs via Secrets do Streamlit
try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    FOOTBALL_API_KEY = st.secrets["FOOTBALL_API_KEY"]
    ODDS_API_KEY = st.secrets["ODDS_API_KEY"]
except Exception as e:
    st.error("Erro nas API Keys. Verifica os Secrets no Streamlit Cloud!")
    st.stop()

# Headers necessários para comunicar com a API-Football
headers_football = {
    "x-rapidapi-key": FOOTBALL_API_KEY,
    "x-rapidapi-host": "v3.football.api-sports.io"
}

# 2. Funções com Cache para poupar os teus 100 pedidos diários grátis
@st.cache_data(ttl=60) # Guarda os dados dos jogos em memória por 60 segundos
def get_jogos_live():
    url = "https://v3.football.api-sports.io/fixtures"
    params = {"live": "all"}
    resposta = requests.get(url, headers=headers_football, params=params)
    if resposta.status_code == 200:
        return resposta.json().get('response', [])
    return []

@st.cache_data(ttl=60)
def get_estatisticas_jogo(fixture_id):
    url = "https://v3.football.api-sports.io/fixtures/statistics"
    params = {"fixture": fixture_id}
    resposta = requests.get(url, headers=headers_football, params=params)
    if resposta.status_code == 200:
        return resposta.json().get('response', [])
    return []

@st.cache_data(ttl=120)
def get_odds_live(equipa_casa, equipa_fora):
    # Pesquisa as odds de futebol na Europa em tempo real
    url = f"https://api.the-odds-api.com/v4/sports/soccer/odds/?apiKey={ODDS_API_KEY}&regions=eu&markets=h2h&oddsFormat=decimal"
    resposta = requests.get(url)
    if resposta.status_code == 200:
        odds_data = resposta.json()
        # Filtro simples: procura se o nome de uma das equipas está na lista das casas de apostas
        for jogo in odds_data:
            if equipa_casa[:5] in jogo['home_team'] or equipa_fora[:5] in jogo['away_team']:
                return jogo['bookmakers']
    return "Odds dinâmicas não encontradas automaticamente pela API."

# 3. Interface Visual e Cérebro IA
st.set_page_config(page_title="AI Betting Pro", layout="wide")
st.title("⚽ AI Betting: Analisador Real-Time")

tab1, tab2 = st.tabs(["🎯 Jogos Ao Vivo (APIs)", "🧠 Análise Manual (Cérebro IA)"])

# ==========================================
# TABA 1: MOTOR DE DADOS REAIS
# ==========================================
with tab1:
    st.header("Análise de Jogos a Decorrer")
    
    # Botão para forçar uma limpeza à cache e buscar novos jogos
    if st.button("🔄 Atualizar Lista de Jogos Ao Vivo"):
        st.cache_data.clear()
    
    # Vai buscar os jogos à API
    jogos = get_jogos_live()
    
    if not jogos:
        st.warning("Não há jogos a decorrer neste momento ou atingiste o limite da API (100 requests).")
    else:
        # Criar um menu limpo para o utilizador escolher o jogo
        opcoes_jogos = {}
        for j in jogos:
            fixture_id = j['fixture']['id']
            tempo = j['fixture']['status']['elapsed']
            casa = j['teams']['home']['name']
            fora = j['teams']['away']['name']
            golos_casa = j['goals']['home']
            golos_fora = j['goals']['away']
            
            nome_display = f"{tempo}' | {casa} {golos_casa} - {golos_fora} {fora}"
            opcoes_jogos[nome_display] = (fixture_id, casa, fora, golos_casa, golos_fora, tempo)
        
        jogo_selecionado = st.selectbox("Escolhe o jogo que queres dissecar:", list(opcoes_jogos.keys()))
        
        # Só gasta pedidos pesados (Estatísticas) quando clicas aqui
        if st.button("Analisar Valor Real (Gastar Request)"):
            fixture_id, casa, fora, golos_casa, golos_fora, tempo = opcoes_jogos[jogo_selecionado]
            
            with st.spinner("A recolher telemetria do jogo e a cruzar com mercados..."):
                stats = get_estatisticas_jogo(fixture_id)
                odds = get_odds_live(casa, fora)
                
                st.subheader(f"📊 Dados Brutos: {casa} vs {fora}")
                col1, col2 = st.columns(2)
                col1.write("**Estatísticas (API-Football):**")
                col1.json(stats)
                col2.write("**Mercado H2H (The-Odds-API):**")
                col2.write(odds)
                
                # --- O CÉREBRO DA IA ENTRA AQUI ---
                st.subheader("🧠 Veredicto do Cérebro Artificial")
                
                prompt_sistema = """
                És um apostador desportivo profissional e um analista tático de futebol de elite. 
                O teu objetivo é encontrar discrepâncias entre as odds e a probabilidade real (Value Bets).
                Analisa as estatísticas reais fornecidas (posse, remates, ataques perigosos) face ao resultado e tempo do jogo.
                Não sejas conservador. Diz exatamente onde está o dinheiro mal posicionado.
                Dá sempre um palpite de Correct Score justificado.
                Se as odds reais não forem passadas, faz a análise com base no valor intrínseco de uma virada/manutenção de resultado.
                Responde de forma estruturada: 
                1. Leitura de Jogo. 
                2. Aposta de Valor Recomendada (Onde está o dinheiro). 
                3. Prognóstico Correct Score.
                """
                
                prompt_usuario = f"Minuto: {tempo}'. Resultado Atual: {casa} {golos_casa} - {golos_fora} {fora}. Estatísticas: {stats}. Odds Atuais: {odds}."
                
                try:
                    # Usamos o gemini-pro para lógica pesada
                    model = genai.GenerativeModel('gemini-1.5-pro-latest') 
                    resposta_ia = model.generate_content(prompt_sistema + "\n\n" + prompt_usuario)
                    st.success(resposta_ia.text)
                except Exception as e:
                    st.error(f"Erro ao contactar a inteligência artificial: {e}")


# ==========================================
# TABA 2: INSERÇÃO MANUAL DE CONTEXTO
# ==========================================
with tab2:
    st.header("Análise Manual (Quando não há dados API)")
    st.markdown("Insere os dados em formato livre para jogos obscuros ou para adicionares contexto humano (ex: lesões, nevoeiro, relvado).")
    
    col1, col2 = st.columns(2)
    with col1:
        jogo_manual = st.text_input("Equipas (Ex: Porto vs Sporting)")
        resultado_minuto = st.text_input("Tempo e Resultado (Ex: 85' | 1-2)")
    with col2:
        odds_mercado = st.text_input("Odds nas Casas (Ex: Casa: 5.0, Empate 3.2, Fora: 1.1)")
        dados_extra = st.text_area("Contexto Estatístico/Humano (Ex: Porto com 80% posse, 10 cantos nos últimos 15 min. Sporting a defender no bloco baixo.)")
    
    if st.button("Análise Profunda com IA"):
        if dados_extra:
            with st.spinner("A fundir o teu conhecimento com o meu modelo desportivo..."):
                model = genai.GenerativeModel('gemini-1.5-pro-latest')
                prompt = f"""
                Age como apostador profissional focado em Value Bets.
                Jogo: {jogo_manual} ao minuto {resultado_minuto}.
                Odds atuais na casa: {odds_mercado}.
                Contexto do utilizador: {dados_extra}.
                Diz-me qual a aposta de valor e dá um correct score justificado de forma fria e analítica.
                """
                analise = model.generate_content(prompt)
                st.success(analise.text)
        else:
            st.warning("Tens de me dar algum contexto para eu conseguir analisar!")