import streamlit as st
import requests
from groq import Groq
import difflib

# ==========================================
# 1. CONFIGURAÇÃO E API KEYS
# ==========================================
try:
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])
    FOOTBALL_API_KEY = st.secrets["FOOTBALL_API_KEY"]
    ODDS_API_KEY = st.secrets["ODDS_API_KEY"]
    ALLSPORTS_API_KEY = st.secrets.get("ALLSPORTS_API_KEY", "")
except Exception as e:
    st.error("Erro nas API Keys. Verifica os Secrets no Streamlit Cloud!")
    st.stop()

headers_football = {
    "x-rapidapi-key": FOOTBALL_API_KEY,
    "x-rapidapi-host": "v3.football.api-sports.io"
}

# ==========================================
# 2. FUNÇÕES DE DADOS (COM CACHE E RESILIÊNCIA)
# ==========================================
@st.cache_data(ttl=60)
def obter_jogos_live_combinados():
    jogos_formatados = []

    # Tentativa 1: API-Football
    try:
        url_1 = "https://v3.football.api-sports.io/fixtures"
        params = {"live": "all"}
        resp_1 = requests.get(url_1, headers=headers_football, params=params, timeout=5)
        dados_1 = resp_1.json()
        
        if resp_1.status_code == 200 and 'response' in dados_1 and isinstance(dados_1['response'], list) and len(dados_1['response']) > 0:
            for j in dados_1['response']:
                jogos_formatados.append({
                    'id': j['fixture']['id'],
                    'tempo': str(j['fixture']['status']['elapsed']),
                    'casa': j['teams']['home']['name'],
                    'fora': j['teams']['away']['name'],
                    'golos_casa': str(j['goals']['home']),
                    'golos_fora': str(j['goals']['away']),
                    'fonte': 'API-Football'
                })
            return jogos_formatados
    except Exception:
        pass 

    # Tentativa 2: AllSportsAPI
    try:
        if ALLSPORTS_API_KEY:
            url_2 = f"https://apiv2.allsportsapi.com/football/?met=Livescore&APIkey={ALLSPORTS_API_KEY}"
            resp_2 = requests.get(url_2, timeout=5)
            dados_2 = resp_2.json()
            
            if resp_2.status_code == 200 and 'result' in dados_2 and isinstance(dados_2['result'], list):
                for j in dados_2['result']:
                    resultado = str(j.get('event_final_result', '0 - 0'))
                    golos = resultado.split('-')
                    g_casa = golos[0].strip() if len(golos) == 2 else "0"
                    g_fora = golos[1].strip() if len(golos) == 2 else "0"
                    
                    jogos_formatados.append({
                        'id': j.get('event_key'),
                        'tempo': str(j.get('event_status', '')).replace("'", ""),
                        'casa': j.get('event_home_team', 'Equipa A'),
                        'fora': j.get('event_away_team', 'Equipa B'),
                        'golos_casa': g_casa,
                        'golos_fora': g_fora,
                        'fonte': 'AllSportsAPI'
                    })
                return jogos_formatados
    except Exception:
        pass

    return jogos_formatados

@st.cache_data(ttl=60)
def obter_estatisticas_combinadas(fixture_id, equipa_casa, equipa_fora):
    stats_finais = {}

    # Fonte 1: API-Football
    try:
        url_1 = "https://v3.football.api-sports.io/fixtures/statistics"
        params_1 = {"fixture": fixture_id}
        resposta_1 = requests.get(url_1, headers=headers_football, params=params_1, timeout=5)
        if resposta_1.status_code == 200:
            dados = resposta_1.json().get('response', [])
            stats_finais['API-Football'] = dados if dados else "Sem estatísticas disponíveis nesta API."
        else:
            stats_finais['API-Football'] = "Erro na API."
    except Exception:
        stats_finais['API-Football'] = "Falha na ligação."

    # Fonte 2: AllSportsAPI
    try:
        if ALLSPORTS_API_KEY:
            url_2 = f"https://apiv2.allsportsapi.com/football/?met=Livescore&APIkey={ALLSPORTS_API_KEY}"
            resposta_2 = requests.get(url_2, timeout=5)
            if resposta_2.status_code == 200:
                dados_all = resposta_2.json().get('result', [])
                encontrou = False
                if dados_all:
                    for jogo in dados_all:
                        if equipa_casa[:5].lower() in jogo.get('event_home_team', '').lower() or equipa_fora[:5].lower() in jogo.get('event_away_team', '').lower():
                            stats_finais['AllSportsAPI'] = jogo.get('statistics', "Jogo encontrado, mas sem quadro de stats.")
                            encontrou = True
                            break
                if not encontrou:
                    stats_finais['AllSportsAPI'] = "Jogo não encontrado nesta API."
    except Exception:
        stats_finais['AllSportsAPI'] = "Falha na ligação."

    return stats_finais

@st.cache_data(ttl=120)
def get_odds_live(equipa_casa, equipa_fora):
    odds_finais = {}
    
    # O "Cérebro" de comparação de texto (Mede a percentagem de semelhança dos nomes)
    def nomes_parecidos(nome_api, nome_odds):
        similaridade = difflib.SequenceMatcher(None, nome_api.lower(), nome_odds.lower()).ratio()
        return similaridade > 0.55 # Se os nomes forem 55% iguais, assumimos que é a mesma equipa

    try:
        url = f"https://api.the-odds-api.com/v4/sports/soccer/odds/?apiKey={ODDS_API_KEY}&regions=eu&markets=h2h&oddsFormat=decimal"
        resposta = requests.get(url, timeout=5)
        if resposta.status_code == 200:
            odds_data = resposta.json()
            encontrou = False
            
            for jogo in odds_data:
                casa_odds = jogo['home_team']
                fora_odds = jogo['away_team']
                
                # Exigimos que AMBAS as equipas correspondam para não haver misturas
                if (nomes_parecidos(equipa_casa, casa_odds) and nomes_parecidos(equipa_fora, fora_odds)) or \
                   (nomes_parecidos(equipa_casa, fora_odds) and nomes_parecidos(equipa_fora, casa_odds)):
                    odds_finais['The-Odds-API'] = jogo['bookmakers']
                    encontrou = True
                    break
                    
            if not encontrou:
                odds_finais['The-Odds-API'] = "Odds não encontradas para este jogo exato."
    except Exception:
        odds_finais['The-Odds-API'] = "Falha na ligação."
        
    return odds_finais

# ==========================================
# 3. FUNÇÕES VISUAIS (TABELAS)
# ==========================================
def desenhar_tabela_stats(stats_brutas):
    if not isinstance(stats_brutas, dict):
        return st.info("Estatísticas não disponíveis neste momento.")
        
    for fonte, dados in stats_brutas.items():
        if isinstance(dados, str):
            if "Sem estatísticas" not in dados:
                st.warning(f"{fonte}: {dados}")
            continue
            
        st.markdown(f"**Fonte:** {fonte}")
        tabela = []
        
        if fonte == 'AllSportsAPI' and isinstance(dados, list):
            for item in dados:
                tabela.append({"🏠 Casa": item.get('home', ''), "📊 Métrica": item.get('type', ''), "✈️ Fora": item.get('away', '')})
                
        elif fonte == 'API-Football' and isinstance(dados, list) and len(dados) == 2:
            stats_casa = dados[0].get('statistics', [])
            stats_fora = dados[1].get('statistics', [])
            for i in range(len(stats_casa)):
                val_casa = str(stats_casa[i].get('value', '0')).replace('None', '0')
                val_fora = str(stats_fora[i].get('value', '0')).replace('None', '0')
                tabela.append({"🏠 Casa": val_casa, "📊 Métrica": stats_casa[i].get('type', ''), "✈️ Fora": val_fora})
        
        if tabela:
            st.dataframe(tabela, use_container_width=True, hide_index=True)
        else:
            st.json(dados)

def desenhar_tabela_odds(odds_brutas, nome_casa):
    if not isinstance(odds_brutas, dict):
        return st.info("Odds não disponíveis neste momento.")

    for fonte, bookmakers in odds_brutas.items():
        if isinstance(bookmakers, str):
            st.warning(f"{fonte}: {bookmakers}")
            continue
            
        st.markdown(f"**Fonte:** {fonte}")
        tabela = []
        
        if isinstance(bookmakers, list):
            for b in bookmakers:
                casa_aposta = b.get('title', 'Desconhecida')
                odd_1, odd_x, odd_2 = "-", "-", "-"
                for mercado in b.get('markets', []):
                    if mercado.get('key') == 'h2h':
                        for opcao in mercado.get('outcomes', []):
                            if opcao.get('name') == 'Draw':
                                odd_x = opcao.get('price')
                            elif nome_casa[:4] in opcao.get('name'):
                                odd_1 = opcao.get('price')
                            else:
                                odd_2 = opcao.get('price')
                
                tabela.append({"Casa de Apostas": casa_aposta, "1 (Casa)": odd_1, "X (Empate)": odd_x, "2 (Fora)": odd_2})
            
            if tabela:
                st.dataframe(tabela, use_container_width=True, hide_index=True)

# ==========================================
# 4. INTERFACE DA APLICAÇÃO
# ==========================================
st.set_page_config(page_title="AI Betting Pro", layout="wide")
st.title("⚽ AI Betting: Analisador Real-Time (Powered by Llama 3.3)")

tab1, tab2 = st.tabs(["🎯 Jogos Ao Vivo (APIs)", "✍️ Análise Manual"])

# === TABA 1: DADOS REAIS ===
with tab1:
    st.header("Análise de Jogos a Decorrer")
    
    if st.button("🔄 Atualizar Lista de Jogos Ao Vivo"):
        st.cache_data.clear()
    
    jogos = obter_jogos_live_combinados()
    
    if not jogos:
        st.warning("Não há jogos a decorrer neste momento ou as APIs esgotaram o limite.")
    else:
        opcoes_jogos = {}
        for j in jogos:
            fixture_id, tempo, casa, fora = j['id'], j['tempo'], j['casa'], j['fora']
            golos_casa, golos_fora, fonte = j['golos_casa'], j['golos_fora'], j['fonte']
            
            nome_display = f"[{fonte}] {tempo}' | {casa} {golos_casa} - {golos_fora} {fora}"
            opcoes_jogos[nome_display] = (fixture_id, casa, fora, golos_casa, golos_fora, tempo)
        
        jogo_selecionado = st.selectbox("Escolhe o jogo:", list(opcoes_jogos.keys()))
        
        if st.button("🧠 Analisar Valor Real"):
            fixture_id, casa, fora, golos_casa, golos_fora, tempo = opcoes_jogos[jogo_selecionado]
            
            with st.spinner("A enviar dados para o Llama 3.3..."):
                stats = obter_estatisticas_combinadas(fixture_id, casa, fora)
                odds = get_odds_live(casa, fora)
                
                st.divider()
                col_s, col_o = st.columns(2)
                with col_s:
                    st.subheader(f"📊 Estatísticas em Campo")
                    desenhar_tabela_stats(stats)
                with col_o:
                    st.subheader(f"💰 Mercado de Odds")
                    desenhar_tabela_odds(odds, casa)
                st.divider()
                
                st.subheader("🧠 Veredicto do Motor Tático")
                prompt_sistema = """
                És um apostador desportivo profissional e um analista tático de elite. 
                O teu objetivo é encontrar discrepâncias matemáticas e contextuais entre as odds do mercado e a probabilidade real dos eventos (Value Bets).
                Vou fornecer-te dados estatísticos e de odds de várias APIs.
                1. Se uma falhar, ignora-a e analisa a que funcionou.
                2. Cruza os dados: Se divergirem, usa a média ou o teu raciocínio.
                3. Se encontrares valor, baseia a tua "Value Bet" na odd mais alta disponível.
                4. REGRA DE OURO: Se não vires valor claro nas odds, ou se o jogo estiver demasiado imprevisível e caótico, NÃO TENHAS MEDO de recomendar "No Bet" (Ficar de fora). Proteger a banca é mais importante do que forçar uma aposta.
                
                Responde SEMPRE em Português de Portugal: 
                1. Leitura de Jogo. 
                2. Aposta de Valor Recomendada (ou explicação de porquê não apostar). 
                3. Prognóstico Correct Score.
                """
                prompt_usuario = f"Minuto: {tempo}'. Resultado Atual: {casa} {golos_casa} - {golos_fora} {fora}. Estatísticas: {stats}. Odds: {odds}."
                
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
                    st.error(f"Erro ao contactar a IA: {e}")

# === TABA 2: MANUAL ===
with tab2:
    st.header("✍️ Inserção Manual de Estatísticas")
    st.markdown("Preenche os dados do jogo. Não precisas de preencher tudo, foca-te no que achares relevante.")
    
    if 'posse_casa' not in st.session_state: st.session_state.posse_casa = 50
    if 'posse_fora' not in st.session_state: st.session_state.posse_fora = 50

    def atualiza_posse_fora(): st.session_state.posse_fora = 100 - st.session_state.posse_casa
    def atualiza_posse_casa(): st.session_state.posse_casa = 100 - st.session_state.posse_fora
    
    st.subheader("📌 Informação Base")
    col1, col2, col3, col4 = st.columns(4)
    with col1: equipa_casa = st.text_input("🏠 Equipa Casa", value="Equipa A")
    with col2: golos_casa = st.number_input("Golos Casa", min_value=0, max_value=20, value=0)
    with col3: golos_fora = st.number_input("Golos Fora", min_value=0, max_value=20, value=0)
    with col4: equipa_fora = st.text_input("✈️ Equipa Fora", value="Equipa B")
        
    col_min, col_odds = st.columns(2)
    with col_min: minuto = st.number_input("⏱️ Minuto do Jogo", min_value=0, max_value=120, value=75)
    with col_odds: odds_mercado = st.text_input("💰 Odds Atuais", placeholder="Ex: Casa 2.10 | X 3.20 | Fora 3.50")

    st.divider()
    st.subheader("📊 Estatísticas do Jogo")
    col_stat1, col_stat2 = st.columns(2)
    
    with col_stat1:
        st.markdown(f"**{equipa_casa} (Casa)**")
        st.number_input("Posse de Bola (%) Casa", min_value=0, max_value=100, key="posse_casa", on_change=atualiza_posse_fora)
        remates_casa = st.number_input("Remates Totais Casa", min_value=0, max_value=50, value=0)
        alvo_casa = st.number_input("Remates à Baliza Casa", min_value=0, max_value=50, value=0)
        cantos_casa = st.number_input("🚩 Cantos Casa", min_value=0, max_value=30, value=0)
        vermelhos_casa = st.number_input("🟥 Vermelhos Casa", min_value=0, max_value=5, value=0)

    with col_stat2:
        st.markdown(f"**{equipa_fora} (Fora)**")
        st.number_input("Posse de Bola (%) Fora", min_value=0, max_value=100, key="posse_fora", on_change=atualiza_posse_casa)
        remates_fora = st.number_input("Remates Totais Fora", min_value=0, max_value=50, value=0)
        alvo_fora = st.number_input("Remates à Baliza Fora", min_value=0, max_value=50, value=0)
        cantos_fora = st.number_input("🚩 Cantos Fora", min_value=0, max_value=30, value=0)
        vermelhos_fora = st.number_input("🟥 Vermelhos Fora", min_value=0, max_value=5, value=0)

    st.divider()
    st.subheader("📝 Contexto Extra (Opcional)")
    dados_extra = st.text_area("Informação humana relevante", placeholder="Ex: Está a chover muito, avançado lesionado...")
    
    if st.button("🧠 Pedir Análise ao Llama 3.3 (Manual)"):
        with st.spinner("A fundir dados e contexto..."):
            contexto_ia = dados_extra if dados_extra else "Sem contexto extra."
            p_casa = st.session_state.posse_casa
            p_fora = st.session_state.posse_fora
            
            prompt_usuario = f"""
            JOGO: {equipa_casa} {golos_casa} - {golos_fora} {equipa_fora} (Minuto {minuto}')
            ODDS ATUAIS: {odds_mercado}
            
            ESTATÍSTICAS {equipa_casa}: Posse {p_casa}%, Remates {remates_casa} (À baliza: {alvo_casa}), Cantos: {cantos_casa}, Vermelhos: {vermelhos_casa}.
            ESTATÍSTICAS {equipa_fora}: Posse {p_fora}%, Remates {remates_fora} (À baliza: {alvo_fora}), Cantos: {cantos_fora}, Vermelhos: {vermelhos_fora}.
            
            CONTEXTO: {contexto_ia}
            """
            try:
                resposta_ia = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[
                        {"role": "system", "content": "Age como apostador profissional focado em Value Bets. Responde sempre em Português de Portugal de forma justificada."},
                        {"role": "user", "content": prompt_usuario}
                    ]
                )
                st.success(resposta_ia.choices[0].message.content)
            except Exception as e:
                st.error(f"Erro na ligação à IA: {e}")