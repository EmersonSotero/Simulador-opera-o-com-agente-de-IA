import gymnasium as gym
from gymnasium import spaces
import numpy as np
import simpy

from simulador_puro_v1 import *

def normalizar(valor, min_val, max_val):
    """Normaliza um valor continuo ou inteiro para o intervalo [0.0, 1.0]."""
    if max_val == min_val:
        return 0.0
    val_norm = (valor - min_val) / (max_val - min_val)
    return float(np.clip(val_norm, 0.0, 1.0))


def desnormalizar_acao(
    acao_modelo, min_real, max_real, min_gym=0, max_gym=1.0
):
    """Converte a ação do Gym (ex: de -1 a 1) para o valor físico real da fábrica (ex: de 40 a 60)."""
    # Clip para garantir que nada passe dos limites do Gym
    acao_climpada = np.clip(acao_modelo, min_gym, max_gym)

    # 1. Transforma de [-1, 1] para a proporção [0, 1]
    proporcao = (acao_climpada - min_gym) / (max_gym - min_gym)

    # 2. Mapeia a proporção na escala real [min_real, max_real]
    vazao_real = min_real + proporcao * (max_real - min_real)

    return float(vazao_real[0]) if hasattr(vazao_real, "__len__") else float(vazao_real)

class NitroceluloseEnv(gym.Env):
    
    def __init__(self, step_duration=1.0, max_sim_time=700.0, logger = None):
        super().__init__()
        self.plano_entrega = []
        self.lista_paradas =[]
        self.logger = logger
        # --- 1. CONFIGURAÇÕES DO SEU SIMULADOR ---
        self.step_duration = step_duration  # De quanto em quanto tempo o SimPy pausa para o Gym
        self.max_sim_time = max_sim_time    # Tempo máximo de execução de um episódio no SimPy


        self.action_space = spaces.Box(
            low=np.array([0.0], dtype=np.float32), 
            high=np.array([1.0], dtype=np.float32), 
            dtype=np.float32
        )

        # 1. Limites físicos da simulação
        self.acao_min = 10.0
        self.acao_max = 150.0

        ####Estados
        #Número de maquinas disponiveis
        #tempo da nitração parada

        # Define os limites inferiores de cada uma das variáveis
        limites_inferiores = np.array([0.0, 0.0,0.0,0.0], dtype=np.float32)

        # Define os limites superiores de cada uma das variáveis
        limites_superiores = np.array([1.0, 1.0,1.0,1.0], dtype=np.float32)

        self.observation_space = spaces.Box(
            low=limites_inferiores,
            high=limites_superiores,
            dtype=np.float32
        )

        self.sim_env = None
        self.fabrica = None

    def reset(self, seed=None, options=None):
        
        #seed aleatória
        super().reset(seed=seed)
        if seed is not None:
            np.random.seed(seed)


        self.logger = Logger()
        self.sim_env = simpy.Environment()

        n1 = Nitrador(self.sim_env, tag="NIT-01", tempo_ciclo=0, logger=self.logger)

        d1 = Digestor(self.sim_env, tag="DIG-01", tempo_ciclo = 40, logger=self.logger)
        d2 = Digestor(self.sim_env, tag="DIG-02", tempo_ciclo=40, logger=self.logger)
        d3 = Digestor(self.sim_env, tag="DIG-03", tempo_ciclo=40, logger=self.logger)

        linha_A_nitracao = Linha(nome="Linha A NITRACAO", tipos_permitidos=["Tipo_A", "Tipo_B"], maquinas=[n1])
        linha_A_digestao = Linha(nome="Linha A DIGESTÂO", tipos_permitidos=["Tipo_A", "Tipo_B"], maquinas=[d1, d2,d3])
        etapa_nitracao = Etapa(self.sim_env, nome="Nitracao", linhas=[linha_A_nitracao])
        etapa_digestao = Etapa(self.sim_env, nome="Digestão", linhas=[linha_A_digestao])



        self.fabrica = Nitrocelulose(
            env=self.sim_env,
            nitracao=etapa_nitracao,
            digestao=etapa_digestao,
            plano_entrega=self.plano_entrega,
            logger=self.logger
        )
        self.adicionar_paradas()

        self.sim_env.process(self.fabrica.gerenciar_processos())
        maquina = self.fabrica.nitracao.linhas[0].maquinas[0]

        # [CHAVE DA SOLUÇÃO]: Fazer a simulação rodar ATÉ a máquina solicitar a ação pela 1ª vez
        self.sim_env.run(until=self.fabrica.nitracao.linhas[0].maquinas[0].evento_acao_necessaria)

        obs = self._get_obs()

        # 6. RETORNAR OBSERVAÇÃO E DICIONÁRIO DE INFORMAÇÕES
        # O Gymnasium EXIGE que o retorno seja uma tupla: (obs, info)
        info = {} 
        return obs, info

    def definir_parada(self, tag,tipo, data_inicio, data_fim):
        self.lista_paradas = [tag,tipo, data_inicio, data_fim]

    def adicionar_paradas(self):
        if len(self.lista_paradas) == 0:
            return
        else:
            self.fabrica.definir_parada(
                self.lista_paradas[0],
                self.lista_paradas[1],                    
                self.lista_paradas[2],
                self.lista_paradas[3]                        
                                    )

    def adicionar_plano_entrega(self,lista):
        self.plano_entrega = lista
    def _get_obs(self):
        """
        Lê os dados em tempo real da instância self.fabrica do SimPy.
        (Ajuste os nomes dos atributos abaixo conforme os nomes reais na sua classe Nitrocelulose)
        """

    # 1. Coleta de valores brutos da fábrica
        maquinas_ativas = self.fabrica.digestao.get_qtde_maquinas_disponiveis()
        tempo_parado = self.fabrica.nitracao.linhas[0].maquinas[0].get_tempo_parado()
        qtd_restante = len(self.fabrica.plano_entrega)
        tempo_percorrido = self.sim_env.now

    # 2. Normalização limpa (Valor, Minimo, Maximo)
        obs_norm = [
        normalizar(maquinas_ativas, min_val=0, max_val=3),
        normalizar(tempo_parado, min_val=0.0, max_val=60),  # ex: 2 horas
        normalizar(qtd_restante, min_val=0, max_val=4),
        normalizar(qtd_restante, min_val=0, max_val=self.max_sim_time),
        ]

        return np.array(obs_norm, dtype=np.float32)

    def step(self, action):
        # 1. Converte a ação em vazão real
        vazao_desejada = desnormalizar_acao(
            action, min_real=self.acao_min, max_real=self.acao_max
        )

        maquina = self.fabrica.nitracao.linhas[0].maquinas[0]

        # 2. Aplica a nova ação na máquina
        maquina.set_vazao(vazao_desejada)

        # 3. Destrava a máquina no SimPy se ela estava aguardando uma ação
        evento_atual = maquina.evento_acao_necessaria
        if evento_atual and not evento_atual.triggered:
            evento_atual.succeed()

        # 4. Prepara um novo evento para a próxima requisição da máquina
        maquina.evento_acao_necessaria = self.sim_env.event()

        # 5. AVANÇA A SIMULAÇÃO
        # Roda o SimPy até o próximo evento da máquina OU até o tempo máximo
        tempo_alvo = self.sim_env.now + self.step_duration
        
        try:
            # Roda até que a máquina pague o 'yield' do novo evento OU até o tempo limite do step
            self.sim_env.run(until=simpy.AnyOf(self.sim_env, [maquina.evento_acao_necessaria, self.sim_env.timeout(self.step_duration)]))
        except RuntimeError:
            pass

        # 6. LEITURA DOS DADOS APÓS O TEMPO AVANÇAR NO SIMPY
        tempo_parado_real = maquina.get_tempo_parado()
        maquinas_livres_real = self.fabrica.digestao.get_qtde_maquinas_disponiveis()
        lotes_restantes = len(self.fabrica.plano_entrega)

        obs = self._get_obs()

        # 7. CÁLCULO DAS PARCELAS DA RECOMPENSA
        r_tempo_parado = -float(tempo_parado_real) * 50.0
        r_vazao = float(vazao_desejada) * 25
        r_maquinas_livres = -float(maquinas_livres_real) * 400
        r_lotes = -float(lotes_restantes) * 25.0

        # 8. REGRAS DE TÉRMINO (TERMINATED)
        terminated = False
        r_penalidade_parada = 0.0

        # Condição 1: Todos os lotes entregues (Vitória)
        if lotes_restantes == 0:
            terminated = True

        # Condição 2: Nitração parada há mais de 60 min (Derrota)
        if tempo_parado_real >= 60.0:
            if lotes_restantes > 1:
                r_penalidade_parada = -1000.0
                terminated = True

        r_tempo_sim = self.sim_env.now * -0.1 
        # RECOMPENSA TOTAL DO PASSO
        recompensa = r_tempo_parado + r_vazao + r_maquinas_livres + r_lotes + r_penalidade_parada + r_tempo_sim

        # Condição de Truncamento (Tempo Máximo do Episódio)
        truncated = float(self.sim_env.now) >= float(self.max_sim_time)

        # 9. LOGS DE INFOS E RECOMPENSAS
        info = {
            "tempo_simulacao": self.sim_env.now,
            "vazao_aplicada": vazao_desejada,
            "tempo_parada_real": tempo_parado_real,
            "digestores_livres": maquinas_livres_real,
            "lotes_restantes": lotes_restantes,
            "tempo_percorrido" : self.sim_env.now,
            "rewards": {
                "r_tempo_parado": r_tempo_parado,
                "r_vazao": r_vazao,
                "r_maquinas_livres": r_maquinas_livres,
                "r_lotes": r_lotes,
                "r_penalidade_parada": r_penalidade_parada,
                "r_total_step": recompensa
            }
        }

        return obs, float(recompensa), terminated, truncated, info