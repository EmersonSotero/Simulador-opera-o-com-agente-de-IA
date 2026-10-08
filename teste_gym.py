import pandas as pd
import plotly.express as px
from gymnasium.utils.env_checker import check_env
from stable_baselines3 import PPO
from simulador_gym_rl_v1 import *


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


def testar_e_detalhar_recompensas(model, env, num_episodios=1):
    """Executa episódios de teste, detalha as recompensas passo a passo, exibe o Logger e gera o Gantt."""
    print("\n" + "=" * 85)
    print(f"--- EXECUTANDO TESTE DETALHADO DE RECOMPENSAS E LOGS ({num_episodios} EPISÓDIO(S)) ---")
    print("=" * 85)

    for ep in range(1, num_episodios + 1):
        obs, info = env.reset()
        done = False
        step_count = 0
        acumulado = {
            "r_tempo_parado": 0.0,
            "r_vazao": 0.0,
            "r_maquinas_livres": 0.0,
            "r_lotes": 0.0,
            "r_penalidade_parada": 0.0,
            "r_total": 0.0
        }

        print(f"\n--- EPISÓDIO {ep} ---")
        header = f"{'Passo':<6} | {'Tempo Sim':<10} | {'Vazão':<8} | {'R(Parada)':<10} | {'R(Vazão)':<9} | {'R(MáqLib)':<9} | {'R(Lotes)':<9} | {'R(Penal)':<8} | {'Total Passo':<11}"
        print(header)
        print("-" * len(header))

        while not done:
            step_count += 1
            action, _states = model.predict(obs, deterministic=True)
            obs, reward, terminated, truncated, info = env.step(action)
            done = terminated or truncated

            rew = info["rewards"]
            
            # Acumula os valores do episódio
            acumulado["r_tempo_parado"] += rew["r_tempo_parado"]
            acumulado["r_vazao"] += rew["r_vazao"]
            acumulado["r_maquinas_livres"] += rew["r_maquinas_livres"]
            acumulado["r_lotes"] += rew["r_lotes"]
            acumulado["r_penalidade_parada"] += rew["r_penalidade_parada"]
            acumulado["r_total"] += reward

            # Tabela passo a passo das recompensas
            print(
                f"{step_count:<6} | "
                f"{info['tempo_simulacao']:<10.2f} | "
                f"{info['vazao_aplicada']:<8.2f} | "
                f"{rew['r_tempo_parado']:<10.2f} | "
                f"{rew['r_vazao']:<9.2f} | "
                f"{rew['r_maquinas_livres']:<9.2f} | "
                f"{rew['r_lotes']:<9.2f} | "
                f"{rew['r_penalidade_parada']:<8.2f} | "
                f"{reward:<11.2f}"
            )

        # Resumo final das recompensas do episódio
        print("\n" + "." * 85)
        print(f"RESUMO DAS RECOMPENSAS - EPISÓDIO {ep}:")
        print(f"  • Total R(Tempo Parado)     : {acumulado['r_tempo_parado']:.2f}")
        print(f"  • Total R(Vazão Aplicada)   : {acumulado['r_vazao']:.2f}")
        print(f"  • Total R(Máquinas Livres)  : {acumulado['r_maquinas_livres']:.2f}")
        print(f"  • Total R(Lotes Restantes)  : {acumulado['r_lotes']:.2f}")
        print(f"  • Total Penalidades Excesso : {acumulado['r_penalidade_parada']:.2f}")
        print(f"  • RECOMPENSA TOTAL ACUMULADA: {acumulado['r_total']:.2f}")
        print("." * 85)

        # =========================================================================
        # EXIBIÇÃO DOS REGISTROS DO LOGGER DA FÁBRICA
        # =========================================================================
        logger_fabrica = getattr(env, "logger", None) or env.fabrica.logger

        if logger_fabrica and hasattr(logger_fabrica, "obter_dataframe_resumo"):
            df_resumo = logger_fabrica.obter_dataframe_resumo()

            print("\n📊 " + "=" * 30 + f" REGISTROS DA FÁBRICA (LOGGER EPISÓDIO {ep}) " + "=" * 30)
            if isinstance(df_resumo, pd.DataFrame) and not df_resumo.empty:
                print(df_resumo.to_string(index=False))
                
                # =========================================================================
                # GERAÇÃO DO GRÁFICO DE GANTT COM OS LOGS OBTIDOS
                # =========================================================================
                print(f"\n📈 Gerando Gráfico de Gantt do Episódio {ep}...")
                gerar_gantt_maquinas(df_resumo)
            else:
                print(df_resumo)
            print("=" * 85)
        else:
            print("\n⚠️ Logger ou método 'obter_dataframe_resumo' não encontrado no ambiente.")

    
def main():
    env = NitroceluloseEnv()
    check_env(env)
    env.adicionar_plano_entrega =  [
            Produto(nome="Lote 01",qtde = 2200, tipo="Tipo_A", digestao_tempo_ciclo=60),
            Produto(nome="Lote 02",qtde = 3300, tipo="Tipo_B", digestao_tempo_ciclo=90),
            Produto(nome="Lote 03",qtde = 2200, tipo="Tipo_A", digestao_tempo_ciclo=62),
            Produto(nome="Lote 04",qtde = 1100, tipo="Tipo_A", digestao_tempo_ciclo=58),
        ]
    print("--- Inicializando o Modelo PPO ---")
    model = PPO(
        policy="MlpPolicy",
        env=env,
        learning_rate=3e-4,
        n_steps=2048,
        batch_size=64,
        verbose=1,
    )

    print("\n--- Iniciando o Treinamento ---")
    TOTAL_TIMESTEPS = 20_000
    model.learn(total_timesteps=TOTAL_TIMESTEPS)

    model_path = "ppo_simpy_fabrica"
    model.save(model_path)
    print(f"\nModelo salvo com sucesso em '{model_path}.zip'")

    # Executa o teste detalhando recompensas, mostrando DF e abrindo o gráfico de Gantt
    testar_e_detalhar_recompensas(model, env, num_episodios=2)


if __name__ == "__main__":
    main()