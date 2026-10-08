from simulador_puro_v1 import *

# 1. Instancia o logger e o ambiente
logger = Logger()
env = simpy.Environment()



# 2. Instancia as máquinas passando o logger
n1 = Nitrador(env, tag="NIT-01", tempo_ciclo=0, logger=logger)

d1 = Digestor(env, tag="DIG-01", tempo_ciclo = 40, logger=logger)
d2 = Digestor(env, tag="DIG-02", tempo_ciclo=40, logger=logger)
d3 = Digestor(env, tag="DIG-03", tempo_ciclo=40, logger=logger)

r1 = Refinador(env, tag="REF-01", tempo_ciclo=10, logger=logger)
r2 = Refinador(env, tag="REF-02", tempo_ciclo=12, logger=logger)

# 3. Cria as linhas de produção
linha_A_nitracao = Linha(nome="Linha A NITRACAO", tipos_permitidos=["Tipo_A", "Tipo_B"], maquinas=[n1])
linha_A_digestao = Linha(nome="Linha A DIGESTÂO", tipos_permitidos=["Tipo_A", "Tipo_B"], maquinas=[d1, d2,d3])
linha_A_refino = Linha(nome="Linha A REFINO", tipos_permitidos=["Tipo_B","Tipo_A"], maquinas=[r1, r2])

# 4. Agrupa as linhas nas etapas
etapa_nitracao = Etapa(env, nome="Nitracao", linhas=[linha_A_nitracao])
etapa_digestao = Etapa(env, nome="Digestão", linhas=[linha_A_digestao])
etapa_refino = Etapa(env, nome="Refino", linhas=[linha_A_refino])

# 5. Define o plano de entrega
plano_entrega = [
    Produto(nome="Lote 01",qtde = 2200, tipo="Tipo_A", digestao_tempo_ciclo=65),
    Produto(nome="Lote 02",qtde = 3300, tipo="Tipo_B", digestao_tempo_ciclo=60),
    Produto(nome="Lote 03",qtde = 2200, tipo="Tipo_A", digestao_tempo_ciclo=62),
    Produto(nome="Lote 04",qtde = 1100, tipo="Tipo_A", digestao_tempo_ciclo=58),
]

# 6. Inicializa o gerenciador
fabrica = Nitrocelulose(
    env=env,
    nitracao=etapa_nitracao,
    digestao=etapa_digestao,
    plano_entrega=plano_entrega,
    logger=logger
)

# 7. Executa a simulação
env.run(until=5000)

# ==========================================
# RESULTADO DOS LOGS
# ==========================================
# A lista `logger.historico_logs` agora contém todos os eventos.
# Exemplo de como visualizar ou exportar:
df_logs = logger.obter_dataframe_resumo()



def gerar_gantt_maquinas(df_resumo):
    """
    Gera um Gráfico de Gantt onde:
    - Eixo Y: Componente (Máquina)
    - Eixo X: Linha do tempo (data_hora_inicio até data_hora_fim)
    - Barras/Cores: Tipo de Ação ou Produto
    """
    # Garante a conversão das colunas de data para o formato datetime
    df = df_resumo.copy()
    df['data_hora_inicio'] = pd.to_datetime(df['data_hora_inicio'])
    df['data_hora_fim'] = pd.to_datetime(df['data_hora_fim'])

    # Criação do gráfico de Gantt
    fig = px.timeline(
        df,
        x_start="data_hora_inicio",
        x_end="data_hora_fim",
        y="componente",
        color="tipo_acao",             # Define a cor baseada no tipo de ação
        text="produto",                # Exibe o nome do produto dentro do bloco
        hover_data=["tempo_inicio", "tempo_fim"],
        labels={
            "componente": "Máquina / Equipamento",
            "tipo_acao": "Tipo de Ação",
            "produto": "Produto/Lote"
        },
        title="Ocupação das Máquinas - Gráfico de Gantt"
    )

    # Ajusta o eixo Y para ordenar as máquinas e exibe o texto dentro das barras
    fig.update_yaxes(autorange="reversed")
    fig.update_traces(textposition="inside")
    
    # Melhora o layout visual
    fig.update_layout(
        xaxis_title="Horário da Simulação",
        yaxis_title="Máquinas",
        legend_title="Tipo de Ação",
        hovermode="closest"
    )

    fig.show()



gerar_gantt_maquinas(df_logs)