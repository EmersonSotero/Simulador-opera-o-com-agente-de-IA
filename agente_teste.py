from simulador_gym_rl_v1 import *
import pandas as pd
import pandas as pd
from stable_baselines3 import PPO
import plotly.express as px

import numpy as np

def desnormalizar_acao(
    acao_modelo, min_real=10.0, max_real=150.0, min_gym=0.0, max_gym=1.0
):
    """Converte a ação recebida do modelo [0.0, 1.0] para o intervalo físico real [min_real, max_real]."""
    
    # 1. Trava o valor no intervalo esperado do Gym [min_gym, max_gym]
    acao_clipada = np.clip(acao_modelo, min_gym, max_gym)

    # 2. Converte para a proporção [0.0, 1.0]
    proporcao = (acao_clipada - min_gym) / (max_gym - min_gym)

    # 3. Mapeia a proporção no intervalo físico real [min_real, max_real]
    vazao_real = min_real + proporcao * (max_real - min_real)

    # 4. Extrai com segurança o escalar em Python float puro
    if isinstance(vazao_real, np.ndarray):
        return float(vazao_real.item() if vazao_real.size == 1 else vazao_real.flat[0])
    
    return float(vazao_real)

def rodar_simulacao_com_agente():
    # 1. Instanciar o ambiente e carregar o modelo treinado
    env = NitroceluloseEnv()
    plano_entrega =  [
                Produto(nome="Lote 01",qtde = 2200, tipo="Tipo_A", digestao_tempo_ciclo=60),
                Produto(nome="Lote 02",qtde = 3300, tipo="Tipo_B", digestao_tempo_ciclo=90),
                Produto(nome="Lote 03",qtde = 2200, tipo="Tipo_A", digestao_tempo_ciclo=62),
                Produto(nome="Lote 04",qtde = 1100, tipo="Tipo_A", digestao_tempo_ciclo=58),
            ]
    env.adicionar_plano_entrega(plano_entrega)
    env.definir_parada("DIG-01","MANUTENÇÃO",datetime(2026, 9, 21, 8, 0),datetime(2026, 9, 21, 13, 0))
    model = PPO.load("ppo_simpy_fabrica")

    obs, info = env.reset()
    done = False
    truncated = False

    passo = 0
    recompensa_acumulada = 0.0
    historico = []

    print("=" * 65)
    print(f"{'Passo':<7} | {'Ação (Modelo)':<15} | {'Ação Real':<12} | {'Recompensa':<10}")
    print("=" * 65)

    while not (done or truncated):
        passo += 1

        # Predict traz a ação no intervalo [-1, 1]
        # deterministic=True garante que o agente use sua melhor política aprendida
        action_model, _states = model.predict(obs, deterministic=True)

        # Converte para a faixa real (40 a 60)
        acao_real = desnormalizar_acao(action_model)

        # Executa o passo no SimPy
        obs, reward, done, truncated, info = env.step(action_model)

        recompensa_acumulada += reward

        # Exibe no terminal
        act_str = f"{float(action_model[0]):.3f}"
        print(f"{passo:<7} | {act_str:<15} | {acao_real:<12.2f} | {reward:<10.2f} | {info['tempo_simulacao']}")

        # Salva os dados para análise
        historico.append(
            {
                "passo": passo,
                "acao_modelo": float(action_model[0]),
                "acao_real": acao_real,
                "recompensa": reward,
            }
        )

    print("=" * 65)
    print(f"Simulação concluída!")
    print(f"Total de Passos: {passo}")
    print(f"Recompensa Acumulada: {recompensa_acumulada:.2f}\n")
    return env


def gerar_gantt_maquinas(df_resumo):
    """
    Gera um Gráfico de Gantt onde:
    - Eixo Y: Componente (Máquina)
    - Eixo X: Linha do tempo (data_hora_inicio até data_hora_fim)
    - Barras/Cores: Tipo de Ação ou Produto
    """
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


if __name__ == "__main__":
    env= rodar_simulacao_com_agente()
    gerar_gantt_maquinas(env.fabrica.logger.obter_dataframe_resumo())