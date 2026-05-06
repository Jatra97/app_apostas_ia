import streamlit as st
import requests
import difflib
from groq import Groq
from datetime import datetime, timedelta

# ==========================================
# 1. CONFIGURAÇÃO E API KEYS
# ==========================================
try:
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])
    FOOTBALL_API_KEY = st.secrets["FOOTBALL_API_KEY"]
    ODDS_API_KEY = st.secrets["ODDS_API_KEY"]
    ODDS_API_IO_KEY = st.secrets.get("ODDS_API_IO_KEY", "")
    ALLSPORTS_API_KEY = st.secrets.get("ALLSPORTS_API_KEY", "")
except Exception as e:
    st.error("Erro nas API Keys. Verifica os Secrets no Streamlit Cloud!")
    st.stop()

headers_football = {
    "x-rapidapi-key": FOOTBALL_API_KEY,
    "x-rapidapi-host": "v3.football.api-sports.io"
}

# ==========================================
# 2. FUNÇÕES DE DADOS (LIVE E PRÉ-JOGO)
# ==========================================

@st.cache_data(ttl=3600)
def obter_jogos_por_data(data_str):
    """Busca jogos agendados para uma data específica (YYYY-MM-DD)"""
    try:
        url = "https://v3.football.api-sports.io/fixtures"
        params = {"date": data_str, "status": "NS"} # NS = Not Started
        res = requests.get(url, headers=headers_football, params=params, timeout=10)
        return res.json().get('response', [])
    except: return []

@st.cache_data(ttl=3600)
def obter_detalhes_pre_jogo(fixture_id):
    """Busca H2H e estatísticas de forma para análise pré-jogo"""
    try:
        url = "https://v3.football.api-sports.io/predictions"
        res = requests.get(url, headers=headers_football, params={"fixture": fixture_id}, timeout=10)
        return res.json().get('response', [{}])[0]
    except: return {}

@st.cache_data(ttl=60)
def obter_jogos_live_combinados():
    jogos_formatados = []
    try:
        url_1 = "https://v3.football.api-sports.io/fixtures"
        params = {"live": "all"}
        resp_1 = requests.get(url_1, headers=headers_football, params=params, timeout=5)
        dados_1 = resp_1.json()
        if resp_1.status_code == 200 and 'response' in dados_1:
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
            if jogos_formatados: return jogos_formatados
    except: pass 

    try:
        if ALLSPORTS_API_KEY:
            url_2 = f"https://apiv2.allsportsapi.com/football/?met=Livescore&APIkey={ALLSPORTS_API_KEY}"
            resp_2 = requests.get(url_2, timeout=5)
            dados_2 = resp_2.json()
            if resp_2.status_code == 200 and 'result' in dados_2:
                for j in dados_2['result']:
                    res = str(j.get('event_final_result', '0 - 0')).split('-')
                    jogos_formatados.append({
                        'id': j.get('event_key'),
                        'tempo': str(j.get('event_status', '')).replace("'", ""),
                        'casa': j.get('event_home_team', 'Equipa A'),
                        'fora': j.get('event_away_team', 'Equipa B'),
                        'golos_casa': res[0].strip() if len(res)==2 else "0",
                        'golos_fora': res[1].strip() if len(res)==2 else "0",
                        'fonte': 'AllSportsAPI'
                    })
    except: pass
    return jogos_formatados

@st.cache_data(ttl=60)
def obter_estatisticas_combinadas(fixture_id, equipa_casa, equipa_fora):
    stats_finais = {}
    try:
        res = requests.get("https://v3.football.api-sports.io/fixtures/statistics", headers=headers_football, params={"fixture": fixture_id}, timeout=5)
        stats_finais['API-Football'] = res.json().get('response', []) if res.status_code==200 else "Indisponível"
    except: stats_finais['API-Football'] = "Erro"

    try:
        if ALLSPORTS_API_KEY:
            res = requests.get(f"https://apiv2.allsportsapi.com/football/?met=Livescore&APIkey={ALLSPORTS_API_KEY}", timeout=5)
            if res.status_code == 200:
                for jogo in res.json().get('result', []):
                    if equipa_casa[:5].lower() in jogo.get('event_home_team','').lower():
                        stats_finais['AllSportsAPI'] = jogo.get('statistics', [])
                        break
    except: pass
    return stats_finais

@st.cache_data(ttl=120)
def obter_odds_combinadas(fixture_id, equipa_casa, equipa_fora):
    odds_finais = {}
    def nomes_parecidos(n1, n2):
        if not n1 or not n2: return False
        return difflib.SequenceMatcher(None, str(n1).lower(), str(n2).lower()).ratio() > 0.45

    try:
        res = requests.get(f"https://api.the-odds-api.com/v4/sports/soccer/odds/?apiKey={st.secrets['ODDS_API_KEY']}&regions=eu&markets=h2h&oddsFormat=decimal", timeout=7)
        if res.status_code == 200:
            for j in res.json():
                if nomes_parecidos(equipa_casa, j['home_team']) and nomes_parecidos(equipa_fora, j['away_team']):
                    odds_finais['The-Odds-API'] = j['bookmakers']
                    break
    except: pass

    try:
        key_io = st.secrets.get("ODDS_API_IO_KEY", "")
        if key_io:
            res = requests.get(f"https://odds-api.io/api/v1/odds?apikey={key_io}", timeout=7)
            if res.status_code == 200:
                for j in res.json():
                    h = j.get('home_team', {}).get('name') or j.get('home_name')
                    if nomes_parecidos(equipa_casa, h):
                        odds_finais['Odds-API-IO'] = j.get('odds', [])
                        break
    except: pass

    try:
        res = requests.get("https://v3.football.api-sports.io/odds/live", headers=headers_football, params={"fixture": fixture_id}, timeout=7)
        if res.status_code == 200 and res.json().get('response'):
            odds_finais['API-Football'] = res.json()['response'][0].get('bookmakers', [])
    except: pass

    return odds_finais

# ==========================================
# 3. FUNÇÕES VISUAIS (TABELAS)
# ==========================================
def desenhar_tabela_stats(stats_brutas):
    for fonte, dados in stats_brutas.items():
        if isinstance(dados, list) and dados:
            st.markdown(f"**Fonte:** {fonte}")
            tabela = []
            if fonte == 'AllSportsAPI':
                for item in dados: tabela.append({"🏠 Casa": item.get('home'), "📊 Métrica": item.get('type'), "✈️ Fora": item.get('away')})
            else:
                s_c, s_f = dados[0].get('statistics', []), dados[1].get('statistics', [])
                for i in range(len(s_c)):
                    tabela.append({"🏠 Casa": s_c[i].get('value','0'), "📊 Métrica": s_c[i].get('type'), "✈️ Fora": s_f[i].get('value','0')})
            st.dataframe(tabela, use_container_width=True, hide_index=True)

def desenhar_tabela_odds(odds_brutas, nome_casa):
    for fonte, bookies in odds_brutas.items():
        if isinstance(bookies, list) and bookies:
            st.markdown(f"**Fonte:** {fonte}")
            tabela = []
            if fonte == 'The-Odds-API':
                for b in bookies:
                    odd_1, odd_x, odd_2 = "-", "-", "-"
                    for m in b.get('markets', []):
                        if m['key'] == 'h2h':
                            for o in m['outcomes']:
                                if o['name'] == 'Draw': odd_x = o['price']
                                elif nome_casa[:4].lower() in o['name'].lower(): odd_1 = o['price']
                                else: odd_2 = o['price']
                    tabela.append({"Casa": b.get('title'), "1": odd_1, "X": odd_x, "2": odd_2})
            elif fonte == 'API-Football':
                for b in bookies:
                    odd_1, odd_x, odd_2 = "-", "-", "-"
                    for bet in b.get('bets', []):
                        if str(bet.get('id')) == '1':
                            for v in bet.get('values', []):
                                if v['value'].lower() == 'home': odd_1 = v['odd']
                                elif v['value'].lower() == 'draw': odd_x = v['odd']
                                elif v['value'].lower() == 'away': odd_2 = v['odd']
                    tabela.append({"Casa": b.get('name'), "1": odd_1, "X": odd_x, "2": odd_2})
            elif fonte == 'Odds-API-IO':
                tabela.append({
                    "Casa": "Mercado Global",
                    "1": next((o.get('value') for o in bookies if o.get('name') == '1'), "-"),
                    "X": next((o.get('value') for o in bookies if o.get('name') == 'X'), "-"),
                    "2": next((o.get('value') for o in bookies if o.get('name') == '2'), "-")
                })
            if tabela:
                st.dataframe(tabela, use_container_width=True, hide_index=True)

# ==========================================
# 4. INTERFACE PRINCIPAL
# ==========================================
st.set_page_config(page_title="AI Betting Pro", layout="wide")
st.title("⚽ AI Betting: Analisador Multi-API")

tab1, tab2, tab3 = st.tabs(["🎯 Jogos Ao Vivo", "✍️ Análise Manual", "📅 Planeamento Pré-Jogo"])

# --- TAB 1: LIVE ---
with tab1:
    if st.button("🔄 Atualizar Jogos"): st.cache_data.clear()
    jogos = obter_jogos_live_combinados()
    if not jogos: st.warning("Sem jogos live.")
    else:
        lista = {f"[{j['fonte']}] {j['tempo']}' | {j['casa']} {j['golos_casa']}-{j['golos_fora']} {j['fora']}": j for j in jogos}
        sel = st.selectbox("Escolhe o jogo:", list(lista.keys()))
        if st.button("🧠 Analisar Jogo"):
            j = lista[sel]
            with st.spinner("A cruzar dados..."):
                st.divider()
                s, o = obter_estatisticas_combinadas(j['id'], j['casa'], j['fora']), obter_odds_combinadas(j['id'], j['casa'], j['fora'])
                c1, c2 = st.columns(2)
                with c1: st.subheader("📊 Stats"); desenhar_tabela_stats(s)
                with c2: st.subheader("💰 Odds"); desenhar_tabela_odds(o, j['casa'])
                st.divider()
                prompt_sis = """És um analista de elite. Compara estatísticas e odds de múltiplas fontes. 
                Identifica a melhor odd. Se não houver valor ou for caótico, recomenda 'No Bet'.
                Responde em Português de Portugal: 1. Leitura de Jogo, 2. Aposta de Valor, 3. Correct Score."""
                res = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role": "system", "content": prompt_sis}, {"role": "user", "content": f"Dados: {s}, Odds: {o}, Placar: {j['casa']} {j['golos_casa']}-{j['golos_fora']} {j['fora']}"}])
                st.success(res.choices[0].message.content)

# --- TAB 2: MANUAL ---
with tab2:
    st.header("✍️ Análise Manual")
    if 'p_casa' not in st.session_state: st.session_state.p_casa = 50
    if 'p_fora' not in st.session_state: st.session_state.p_fora = 50
    def up_f(): st.session_state.p_fora = 100 - st.session_state.p_casa
    def up_c(): st.session_state.p_casa = 100 - st.session_state.p_fora
    
    c1, c2, c3, c4 = st.columns(4)
    casa_m = c1.text_input("Casa", "Equipa A")
    g_c = c2.number_input("G Casa", 0)
    g_f = c3.number_input("G Fora", 0)
    fora_m = c4.text_input("Fora", "Equipa B")
    
    col_s1, col_s2 = st.columns(2)
    with col_s1:
        st.number_input("Posse %", 0, 100, key="p_casa", on_change=up_f)
        rem_c = st.number_input("Remates Casa", 0)
        can_c = st.number_input("Cantos Casa", 0)
    with col_s2:
        st.number_input("Posse %", 0, 100, key="p_fora", on_change=up_c)
        rem_f = st.number_input("Remates Fora", 0)
        can_f = st.number_input("Cantos Fora", 0)
        
    contexto = st.text_area("Contexto Extra")
    if st.button("🧠 Analisar Manual"):
        p_sis = "Apostador profissional. Se não houver valor, diz 'No Bet'. Português de Portugal."
        prompt_u = f"{casa_m} {g_c}-{g_f} {fora_m}. Stats: Posse {st.session_state.p_casa}%, Remates {rem_c}, Cantos {can_c}. Contexto: {contexto}"
        res = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role": "system", "content": p_sis}, {"role": "user", "content": prompt_u}])
        st.success(res.choices[0].message.content)

# --- TAB 3: PRÉ-JOGO (COM FILTRO POR PAÍS) ---
with tab3:
    st.header("📅 Planeamento Próximos Jogos")
    col_d, col_p = st.columns(2)
    data_sel = col_d.date_input("Data do Jogo:", datetime.now() + timedelta(days=1))
    
    jogos_f = obter_jogos_por_data(data_sel.strftime("%Y-%m-%d"))
    
    if not jogos_f:
        st.info("Não foram encontrados jogos agendados para esta data.")
    else:
        # Extrair países únicos e ordenar alfabeticamente
        lista_paises = sorted(list(set([j['league']['country'] for j in jogos_f])))
        sel_pais = col_p.selectbox("Escolher País:", lista_paises)
        
        # Filtrar jogos apenas do país selecionado
        jogos_filtrados = [j for j in jogos_f if j['league']['country'] == sel_pais]
        
        # Agrupar por Liga para ficar ainda mais bonito no Selectbox
        opcoes_f = {f"[{j['league']['name']}] {j['teams']['home']['name']} vs {j['teams']['away']['name']}": j for j in jogos_filtrados}
        sel_f = st.selectbox("Selecione o jogo:", list(opcoes_f.keys()))
        
        if st.button("🔍 Analisar Histórico"):
            jogo_d = opcoes_f[sel_f]
            with st.spinner(f"A recolher dados de {sel_pais}..."):
                detalhes = obter_detalhes_pre_jogo(jogo_d['fixture']['id'])
                
                if detalhes:
                    st.divider()
                    col_h, col_a = st.columns(2)
                    with col_h:
                        st.subheader("🏠 " + jogo_d['teams']['home']['name'])
                        st.write(f"**Forma Recente:** {detalhes.get('teams', {}).get('home', {}).get('league', {}).get('form', 'N/A')}")
                    with col_a:
                        st.subheader("✈️ " + jogo_d['teams']['away']['name'])
                        st.write(f"**Forma Recente:** {detalhes.get('teams', {}).get('away', {}).get('league', {}).get('form', 'N/A')}")
                    
                    st.divider()
                    st.subheader("🧠 Veredicto Preditivo Llama 3.3")
                    
                    p_pre = f"""Analisa este jogo de Pré-Jogo: {sel_f} ({sel_pais}).
                    HISTÓRICO E FORMA: {detalhes.get('comparison')}
                    PREVISÃO API: {detalhes.get('predictions', {}).get('advice')}
                    FORÇA EQUIPAS: {detalhes.get('teams')}
                    
                    Tarefa: Com base na forma atual e confrontos diretos, recomenda o melhor mercado (ML, Over/Under ou Ambas Marcam). 
                    Se vires risco excessivo, recomenda 'No Bet'. Responde sempre em Português de Portugal."""
                    
                    res_ia = client.chat.completions.create(
                        model="llama-3.3-70b-versatile",
                        messages=[{"role": "system", "content": "Especialista em prognósticos de futebol profissional."}, {"role": "user", "content": p_pre}]
                    )
                    st.success(res_ia.choices[0].message.content)