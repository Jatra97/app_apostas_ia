import streamlit as st
import requests
from groq import Groq

# 1. Configuração das APIs via Secrets
try:
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])
    FOOTBALL_API_KEY = st.secrets["FOOTBALL_API_KEY"]
    ODDS_API_KEY = st.secrets["ODDS_API_KEY"]
    ALLSPORTS_API_KEY = st.secrets.get("ALLSPORTS_API_KEY", "") # O .get evita erros se te esqueceres de colocar a chave
except Exception as e:
    st.error("Erro nas API Keys.")
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
def obter_estatisticas_combinadas(fixture_id, equipa_casa, equipa_fora):
    stats_finais = {}

    # ==========================================
    # FONTE 1: API-Football (Principal)
    # ==========================================
    try:
        url_1 = "https://v3.football.api-sports.io/fixtures/statistics"
        params_1 = {"fixture": fixture_id}
        resposta_1 = requests.get(url_1, headers=headers_football, params=params_1, timeout=5)
        
        if resposta_1.status_code == 200:
            dados = resposta_1.json().get('response', [])
            if dados:
                stats_finais['API-Football'] = dados
            else:
                stats_finais['API-Football'] = "Sem estatísticas disponíveis nesta API."
        else:
            stats_finais['API-Football'] = "Erro na API."
    except Exception:
        stats_finais['API-Football'] = "Falha na ligação (Timeout)."

    # ==========================================
    # FONTE 2: AllSportsAPI (Backup/Cruzamento)
    # ==========================================
    try:
        if ALLSPORTS_API_KEY:
            # Pede todos os jogos ao vivo na AllSportsAPI
            url_2 = f"https://apiv2.allsportsapi.com/football/?met=Livescore&APIkey={ALLSPORTS_API_KEY}"
            resposta_2 = requests.get(url_2, timeout=5)
            
            if resposta_2.status_code == 200:
                dados_all = resposta_2.json().get('result', [])
                encontrou_jogo = False
                
                # Procura o nosso jogo no meio dos jogos live deles
                if dados_all:
                    for jogo in dados_all:
                        # Comparamos os primeiros 5 caracteres do nome para evitar erros de formatação (ex: "Man Utd" vs "Manchester United")
                        if equipa_casa[:5].lower() in jogo.get('event_home_team', '').lower() or \
                           equipa_fora[:5].lower() in jogo.get('event_away_team', '').lower():
                            
                            # Guarda as estatísticas deles (se existirem)
                            stats_finais['AllSportsAPI'] = jogo.get('statistics', "Jogo encontrado, mas sem quadro de stats.")
                            encontrou_jogo = True
                            break
                            
                if not encontrou_jogo:
                    stats_finais['AllSportsAPI'] = "Jogo não encontrado nos live scores desta API."
        else:
             stats_finais['AllSportsAPI'] = "Chave da AllSportsAPI não configurada."
    except Exception:
        stats_finais['AllSportsAPI'] = "Falha na ligação (Timeout)."

    return stats_finais

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
És um apostador desportivo profissional e um analista tático de elite. 
O teu objetivo é encontrar discrepâncias matemáticas e contextuais entre as odds do mercado e a probabilidade real dos eventos (Value Bets).

ATENÇÃO AOS DADOS (SISTEMA MULTI-API):
Vou fornecer-te dados estatísticos e de odds provenientes de várias APIs diferentes (API-Football, AllSportsAPI, The-Odds-API, etc).
1. Degradação Graciosa: Se uma das fontes falhar, devolver erro ou "indisponível", ignora-a completamente e analisa apenas os dados da API que funcionou.
2. Cruzamento de Dados: Se as estatísticas das duas APIs divergirem ligeiramente (ex: a API 1 diz 5 remates, a API 2 diz 6), assume uma média aproximada e aplica o teu raciocínio tático.
3. Caça ao Valor: Avalia todas as casas de apostas fornecidas e baseia a tua "Value Bet" sempre na odd mais alta disponível.

Responde SEMPRE em Português de Portugal, de forma fria e estruturada: 
1. Leitura de Jogo (O que a estatística cruzada nos diz sobre a pressão e o rumo da partida). 
2. Aposta de Valor Recomendada (Justifica taticamente e indica qual a melhor odd a aproveitar). 
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
    st.header("✍️ Inserção Manual de Estatísticas")
    st.markdown("Preenche os dados do jogo. Não precisas de preencher tudo, foca-te no que achares relevante.")
    
    # --- Lógica de Sincronização da Posse de Bola ---
    if 'posse_casa' not in st.session_state:
        st.session_state.posse_casa = 50
    if 'posse_fora' not in st.session_state:
        st.session_state.posse_fora = 50

    def atualiza_posse_fora():
        st.session_state.posse_fora = 100 - st.session_state.posse_casa

    def atualiza_posse_casa():
        st.session_state.posse_casa = 100 - st.session_state.posse_fora
    # ------------------------------------------------
    
    # 1. Informação Base
    st.subheader("📌 Informação Base")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        equipa_casa = st.text_input("🏠 Equipa Casa", value="Equipa A")
    with col2:
        golos_casa = st.number_input("Golos Casa", min_value=0, max_value=20, value=0)
    with col3:
        golos_fora = st.number_input("Golos Fora", min_value=0, max_value=20, value=0)
    with col4:
        equipa_fora = st.text_input("✈️ Equipa Fora", value="Equipa B")
        
    col_min, col_odds = st.columns(2)
    with col_min:
        minuto = st.number_input("⏱️ Minuto do Jogo", min_value=0, max_value=120, value=75)
    with col_odds:
        odds_mercado = st.text_input("💰 Odds Atuais", placeholder="Ex: Casa 2.10 | X 3.20 | Fora 3.50")

    st.divider()

    # 2. Estatísticas Detalhadas
    st.subheader("📊 Estatísticas do Jogo")
    col_stat1, col_stat2 = st.columns(2)
    
    with col_stat1:
        st.markdown(f"**Estatísticas: {equipa_casa} (Casa)**")
        # Posse ligada à memória
        st.number_input("Posse de Bola (%) Casa", min_value=0, max_value=100, key="posse_casa", on_change=atualiza_posse_fora)
        remates_casa = st.number_input("Remates Totais Casa", min_value=0, max_value=50, value=0)
        alvo_casa = st.number_input("Remates à Baliza Casa", min_value=0, max_value=50, value=0)
        cantos_casa = st.number_input("🚩 Cantos Casa", min_value=0, max_value=30, value=0)
        vermelhos_casa = st.number_input("🟥 Cartões Vermelhos Casa", min_value=0, max_value=5, value=0)

    with col_stat2:
        st.markdown(f"**Estatísticas: {equipa_fora} (Fora)**")
        # Posse ligada à memória
        st.number_input("Posse de Bola (%) Fora", min_value=0, max_value=100, key="posse_fora", on_change=atualiza_posse_casa)
        remates_fora = st.number_input("Remates Totais Fora", min_value=0, max_value=50, value=0)
        alvo_fora = st.number_input("Remates à Baliza Fora", min_value=0, max_value=50, value=0)
        cantos_fora = st.number_input("🚩 Cantos Fora", min_value=0, max_value=30, value=0)
        vermelhos_fora = st.number_input("🟥 Cartões Vermelhos Fora", min_value=0, max_value=5, value=0)

    st.divider()

    # 3. Contexto Opcional
    st.subheader("📝 Contexto Extra (Opcional)")
    dados_extra = st.text_area("Informação humana relevante", placeholder="Ex: Está a chover muito, o melhor avançado da casa saiu lesionado, a equipa visitante está a defender muito recuada...")
    
    # Botão de Ação
    if st.button("🧠 Pedir Análise ao Llama 3.3"):
        with st.spinner("A fundir dados e contexto..."):
            
            contexto_ia = dados_extra if dados_extra else "Nenhum contexto extra fornecido. Baseia-te apenas na estatística."
            
            # Aqui vamos buscar os valores da posse à memória para enviar à IA
            p_casa = st.session_state.posse_casa
            p_fora = st.session_state.posse_fora
            
            prompt_usuario = f"""
            Analisa os seguintes dados deste jogo ao vivo e encontra a Value Bet.
            
            JOGO: {equipa_casa} {golos_casa} - {golos_fora} {equipa_fora} (Minuto {minuto}')
            ODDS ATUAIS: {odds_mercado}
            
            ESTATÍSTICAS {equipa_casa}: Posse {p_casa}%, Remates {remates_casa} (À baliza: {alvo_casa}), Cantos: {cantos_casa}, Vermelhos: {vermelhos_casa}.
            ESTATÍSTICAS {equipa_fora}: Posse {p_fora}%, Remates {remates_fora} (À baliza: {alvo_fora}), Cantos: {cantos_fora}, Vermelhos: {vermelhos_fora}.
            
            CONTEXTO HUMANO: {contexto_ia}
            """
            
            prompt_sistema = "Age como apostador profissional focado em Value Bets. Responde sempre em Português de Portugal. Dá a aposta de valor e correct score de forma justificada."
            
            try:
                resposta_ia = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[
                        {"role": "system", "content": prompt_sistema},
                        {"role": "user", "content": prompt_usuario}
                    ]
                )
                st.success(resposta_ia.choices[0].message.content)
            except Exception as e:
                st.error(f"Erro na ligação à IA: {e}")