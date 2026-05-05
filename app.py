import streamlit as st
import json

# --- Configuração da Página ---
st.set_page_config(page_title="AI Betting Analyzer", layout="wide")
st.title("⚽ AI Betting Analyzer & Value Finder")

# --- Tabs da Aplicação ---
tab1, tab2 = st.tabs(["📊 Jogos Live (API)", "✍️ Inserção Manual (Cérebro IA)"])

# ==========================================
# TABA 1: DADOS AUTOMÁTICOS (APIs)
# ==========================================
with tab1:
    st.header("Análise Automática de Jogos em Direto")
    
    # Simulação de seleção de jogo (Na prática viria da API-Football)
    jogo_selecionado = st.selectbox("Escolhe um jogo a decorrer:", 
                                    ["Benfica vs FC Porto (Minuto 65')", "Real Madrid vs Man City (Minuto 80')"])
    
    if st.button("Analisar Jogo e Procurar Valor"):
        st.info("A ir buscar dados à API-Football e Odds-API...")
        
        # --- AQUI ENTRA O TEU CÓDIGO DE API REAL ---
        # 1. requests.get("url_api_football...")
        # 2. requests.get("url_odds_api...")
        
        # Dados simulados que a API te daria
        dados_simulados = {
            "tempo": "65",
            "resultado": "0-1",
            "estatisticas": {
                "Equipa da Casa": {"posse": 68, "remates_baliza": 8, "ataques_perigosos": 54, "red_cards": 0},
                "Equipa Fora": {"posse": 32, "remates_baliza": 1, "ataques_perigosos": 12, "red_cards": 1}
            },
            "odds_atuais": {"Casa": 3.20, "Empate": 2.50, "Fora": 1.80}
        }
        
        st.json(dados_simulados) # Mostra os dados crus na app
        
        st.subheader("🧠 Análise da IA:")
        # --- AQUI CHAMAS A API DO GEMINI/CHATGPT ---
        # Exemplo de como a IA responderia com base num bom prompt:
        resposta_ia = """
        **🔥 Dinheiro Escondido (Value Bet):** Vitória da Equipa da Casa (Odd 3.20).
        **Justificação:** A equipa da casa está a perder, mas tem 68% de posse de bola, 8 remates à baliza e a equipa visitante tem um jogador a menos (red card). A pressão é avassaladora e a odd de 3.20 para a reviravolta tem um valor esperado positivo (EV+) altíssimo. A casa de apostas está a reagir apenas ao resultado e não à dinâmica do jogo.
        
        **🎯 Correct Score Prognóstico:** 2-1 para a Equipa da Casa.
        """
        st.success(resposta_ia)


# ==========================================
# TABA 2: INSERÇÃO MANUAL
# ==========================================
with tab2:
    st.header("Análise Manual (Jogos sem API)")
    st.markdown("Insere os dados que tens sobre o jogo. A IA vai usar o seu raciocínio futebolístico e contextual (lesões, motivação, relvado) para analisar.")
    
    col1, col2 = st.columns(2)
    with col1:
        equipa_a = st.text_input("Equipa A (Casa)")
        contexto_a = st.text_area("Contexto Equipa A (Ex: Precisa de ganhar para não descer, PL titular lesionado)")
    with col2:
        equipa_b = st.text_input("Equipa B (Fora)")
        contexto_b = st.text_area("Contexto Equipa B (Ex: Já foi campeã, vai rodar a equipa)")
        
    odds_mercado = st.text_input("Odds que encontraste no mercado (Ex: 1: 2.10 | X: 3.00 | 2: 3.50)")
    
    if st.button("Pedir Análise ao Cérebro IA"):
        # Vais compilar isto num prompt e enviar para a API da IA
        prompt = f"Analisa o jogo {equipa_a} vs {equipa_b}. Contexto A: {contexto_a}. Contexto B: {contexto_b}. Odds: {odds_mercado}. Onde está o valor?"
        
        with st.spinner("A analisar o contexto tático e psicológico..."):
            # Simulação da resposta da IA
            st.write("### O Veredicto da IA")
            st.write(f"**Análise de Risco:** O mercado está a dar favoritismo ao {equipa_a} com uma odd de 2.10, mas ignoram que o {equipa_b}, mesmo rodando a equipa, tem jovens da formação a querer mostrar serviço contra uma equipa nervosa por causa da despromoção.")
            st.write("**Aposta Recomendada:** Empate anula aposta (Draw No Bet) no {equipa_b}.")
            st.write("**Prognóstico Correct Score:** 1-1 ou 0-1.")