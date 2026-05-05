import streamlit as st
import requests
from groq import Groq

# 1. Configuração das APIs via Secrets
try:
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])
    FOOTBALL_API_KEY = st.secrets["FOOTBALL_API_KEY"]
    ODDS_API_KEY = st.secrets["ODDS_API_KEY"]
except Exception as e:
    st.error("Erro nas API Keys. Verifica os Secrets no Streamlit Cloud!")
    st.stop()

headers_football = {
    "x-rapidapi-key": FOOTBALL_API_KEY,
    "x-rapidapi-host": "v3.football.api-sports.io"
}

# 2. Funções com Cache
@st.cache_data(ttl=60)
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
    url = f"https://api.the-odds-api.com/v4/sports/soccer/odds/?apiKey={ODDS_API_KEY}&regions=eu&markets=h2h&oddsFormat=decimal"
    resposta = requests.get(url)
    if resposta.status_code == 200:
        odds_data = resposta.json()
        for jogo in odds_data:
            if equipa_casa[:5] in jogo['home_team'] or equipa_fora[:5] in jogo['away_team']:
                return jogo['bookmakers']
    return "Odds dinâmicas não encontradas automaticamente."

# 3. Interface Visual
st.set_page_config(page_title="AI Betting Pro", layout="wide")
st.title("⚽ AI Betting: Analisador Real-Time (Powered by Llama 3)")

tab1, tab2 = st.tabs(["🎯 Jogos Ao Vivo (APIs)", "🧠 Análise Manual"])

# === TABA 1: DADOS REAIS ===
with tab1:
    st.header("Análise de Jogos a Decorrer")
    
    if st.button("🔄 Atualizar Lista de Jogos Ao Vivo"):
        st.cache_data.clear()
    
    jogos = get_jogos_live()
    
    if not jogos:
        st.warning("Não há jogos a decorrer ou atingiste o limite da API-Football (100 requests).")
    else:
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
        
        jogo_selecionado = st.selectbox("Escolhe o jogo:", list(opcoes_jogos.keys()))
        
        if st.button("Analisar Valor Real (Gastar Request)"):
            fixture_id, casa, fora, golos_casa, golos_fora, tempo = opcoes_jogos[jogo_selecionado]
            
            with st.spinner("A enviar dados para a IA (Llama 3)..."):
                stats = get_estatisticas_jogo(fixture_id)
                odds = get_odds_live(casa, fora)
                
                st.subheader(f"📊 Dados: {casa} vs {fora}")
                col1, col2 = st.columns(2)
                col1.json(stats)
                col2.write(odds)
                
                st.subheader("🧠 Veredicto do Llama 3")
                
                prompt_sistema = """
                És um apostador desportivo profissional e analista tático. 
                O teu objetivo é encontrar discrepâncias entre as odds e a probabilidade real (Value Bets).
                Responde SEMPRE em Português de Portugal de forma estruturada: 
                1. Leitura de Jogo. 
                2. Aposta de Valor Recomendada. 
                3. Prognóstico Correct Score.
                """
                prompt_usuario = f"Minuto: {tempo}'. Resultado Atual: {casa} {golos_casa} - {golos_fora} {fora}. Estatísticas: {stats}. Odds: {odds}."
                
                try:
                    resposta_ia = client.chat.completions.create(
                        model="llama-3.3-70b-versatile", # O modelo gratuito e super inteligente da Meta
                        messages=[
                            {"role": "system", "content": prompt_sistema},
                            {"role": "user", "content": prompt_usuario}
                        ]
                    )
                    st.success(resposta_ia.choices[0].message.content)
                except Exception as e:
                    st.error(f"Erro ao contactar a IA: {e}")

# === TABA 2: MANUAL ===
with tab2:
    st.header("Análise Manual")
    col1, col2 = st.columns(2)
    with col1:
        jogo_manual = st.text_input("Equipas (Ex: Porto vs Sporting)")
        resultado_minuto = st.text_input("Tempo e Resultado (Ex: 85' | 1-2)")
    with col2:
        odds_mercado = st.text_input("Odds nas Casas (Ex: Casa: 5.0, Empate 3.2, Fora: 1.1)")
        dados_extra = st.text_area("Contexto Estatístico/Humano")
    
    if st.button("Análise Profunda com IA"):
        if dados_extra:
            with st.spinner("A analisar com Llama 3..."):
                try:
                    resposta_ia = client.chat.completions.create(
                        model="llama-3.3-70b-versatile",
                        messages=[
                            {"role": "system", "content": "Age como apostador profissional focado em Value Bets. Responde em Português de Portugal. Dá a aposta de valor e correct score."},
                            {"role": "user", "content": f"Jogo: {jogo_manual} aos {resultado_minuto}. Odds: {odds_mercado}. Contexto: {dados_extra}."}
                        ]
                    )
                    st.success(resposta_ia.choices[0].message.content)
                except Exception as e:
                    st.error(f"Erro: {e}")
        else:
            st.warning("Insere algum contexto!")