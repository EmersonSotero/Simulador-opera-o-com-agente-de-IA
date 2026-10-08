import simpy
from datetime import datetime, timedelta

import pandas as pd
from itertools import groupby
from operator import itemgetter

class Logger:
    def __init__(self, data_inicio=datetime(2026, 9, 21, 8, 0)):
        self.data_inicio = data_inicio if data_inicio else datetime.now()
        self.historico_logs = []

    def obter_data_hora_atual(self, sim_time):
        """Converte o tempo do SimPy (sim_time) em datetime real."""
        return self.data_inicio + timedelta(minutes=sim_time)

    def obter_sim_time(self, data_hora_target: datetime) -> float:
            diferenca = data_hora_target - self.data_inicio
            return diferenca.total_seconds() / 60.0

    def registrar(self, env, produto, tipo_acao, componente, acao, linha = None, etapa = None,media_vazao = None,qtde_produzida = None):
        """Registra um evento pontual no histórico."""
        timestamp_real = self.obter_data_hora_atual(env.now)
        
        # Aceita tanto objeto produto com atributo .nome quanto string direta
        nome_produto = produto.nome if hasattr(produto, 'nome') else (produto if produto else "")
        
        self.historico_logs.append({
            "tempo_simulado": env.now,
            "data_hora": timestamp_real.strftime("%Y-%m-%d %H:%M:%S"),
            "produto": nome_produto,
            "tipo_acao": tipo_acao,
            "componente": componente,
            "acao": acao,
            "media_vazao": media_vazao,
            "qtde_produzida": qtde_produzida
        })

    def registrar_manual(self, data_hora, produto, tipo_acao, componente, acao, linha = None, etapa = None):
        timestamp_real = self.obter_data_hora_atual(data_hora)
        nome_produto = produto.nome if hasattr(produto, 'nome') else (produto if produto else "")
                
        self.historico_logs.append({
            "tempo_simulado": data_hora,
            "data_hora": timestamp_real.strftime("%Y-%m-%d %H:%M:%S"),
            "produto": nome_produto,
            "tipo_acao": tipo_acao,
            "componente": componente,
            "acao": acao,
            "media_vazao": "",
            "qtde_produzida": ""
        })


    def obter_resumo_agrupado_old(self):
        """
        Consolida eventos mapeando Início e Fim por (componente, tipo_acao).
        """
        operacoes_em_andamento = {} # Chave: (componente, tipo_acao)
        resumo_final = []

        for log in self.historico_logs:
            prod = log['produto']
            comp = log['componente']
            tipo = log['tipo_acao']
            acao = log['acao'].lower()
            
            # A chave de controle é baseada apenas no Equipamento + Tipo de Ação
            chave = (comp, tipo)

            # Detecta palavras-chave de abertura e fechamento
            is_inicio = any(p in acao for p in ['início', 'inicio', 'recebendo', 'entrou'])
            is_fim = any(p in acao for p in ['fim', 'término', 'termino', 'finalizou', 'concluído', 'concluido'])

            if is_inicio:
                # Inicia uma nova operação para o componente e tipo de ação
                operacoes_em_andamento[chave] = {
                    'produto': prod,
                    'componente': comp,
                    'tipo_acao': tipo,
                    'tempo_inicio': log['tempo_simulado'],
                    'tempo_fim': log['tempo_simulado'],
                    'data_hora_inicio': log['data_hora'],
                    'data_hora_fim': log['data_hora']
                }
            elif is_fim:
                if chave in operacoes_em_andamento:
                    # Encerra o ciclo aberto para esse equipamento e ação
                    op = operacoes_em_andamento.pop(chave)
                    op['tempo_fim'] = log['tempo_simulado']
                    op['data_hora_fim'] = log['data_hora']
                    
                    # Atualiza o produto se o início foi 'N/A' mas o fim trouxe a identificação (ou vice-versa)
                    if op['produto'] == 'N/A' and prod != 'N/A':
                        op['produto'] = prod
                        
                    resumo_final.append(op)
                else:
                    # Caso não haja um registro de início prévio capturado
                    resumo_final.append({
                        'produto': prod,
                        'componente': comp,
                        'tipo_acao': tipo,
                        'tempo_inicio': log['tempo_simulado'],
                        'tempo_fim': log['tempo_simulado'],
                        'data_hora_inicio': log['data_hora'],
                        'data_hora_fim': log['data_hora']
                    })

        # Adiciona pendências que não fecharam até o fim da simulação
        for op in operacoes_em_andamento.values():
            resumo_final.append(op)

        for item in resumo_final:
            item['tempo_percorrido'] = float(item['tempo_fim']) - float(item['tempo_inicio'])

        return resumo_final



    def obter_resumo_agrupado(self):
        """Agrupa os registros de historico_logs por componente, produto e tipo_acao

        unindo os pares (1º com 2º, 3º com 4º) mantendo os valores do último
        registro.
        """
        # Trata o caso de histórico vazio para evitar erros
        if not self.historico_logs:
            return []

        # Chaves pelas quais vamos agrupar
        chaves_agrupamento = itemgetter("componente", "produto", "tipo_acao")

        # 1. Ordena os registros do historico_logs da classe
        registros_ordenados = sorted(
            self.historico_logs,
            key=lambda x: (chaves_agrupamento(x), x["tempo_simulado"]),
        )

        resultado = []

        # 2. Agrupa os elementos pelas chaves informadas
        for chave, grupo in groupby(
            registros_ordenados, key=chaves_agrupamento
        ):
            lista_grupo = list(grupo)

            # 3. Itera de 2 em 2 dentro do mesmo grupo
            for i in range(0, len(lista_grupo), 2):
                primeiro = lista_grupo[i]

                # Caso o grupo tenha número ímpar, o último registro usa ele mesmo como segundo
                segundo = (
                    lista_grupo[i + 1]
                    if (i + 1) < len(lista_grupo)
                    else primeiro
                )

                # 4. Criar o novo registro combinado baseado no 'segundo' (valores mais recentes)
                novo_registro = segundo.copy()

                # Removemos a chave 'data_hora' original para não duplicar/confundir
                novo_registro.pop("data_hora", None)

                # CORREÇÃO AQUI: 'tempo_fim' agora usa 'segundo'
                novo_registro["tempo_inicio"] = primeiro["tempo_simulado"]
                novo_registro["tempo_fim"] = segundo["tempo_simulado"]

                # Novas colunas de data/hora
                novo_registro["data_hora_inicio"] = primeiro["data_hora"]
                novo_registro["data_hora_fim"] = segundo["data_hora"]

                # Cálculo correto da duração da etapa
                novo_registro["tempo_percorrido"] = (
                    novo_registro["tempo_fim"] - novo_registro["tempo_inicio"]
                )

                resultado.append(novo_registro)

        return resultado

    
    def obter_dataframe_resumo(self):
        """Retorna o resumo consolidado direto como um DataFrame do Pandas."""
        return pd.DataFrame(self.obter_resumo_agrupado())

class Produto:
    def __init__(self, nome, tipo, qtde, digestao_tempo_ciclo):
        self.nome = nome
        self.digestao_tempo_ciclo = digestao_tempo_ciclo
        self.tipo = tipo
        self.qtde = qtde


class status_maquina:
    def __init__(self, tipo, data_inicio=None, data_fim=None):
        self.tipo = tipo
        self.data_inicio = data_inicio
        self.data_fim = data_fim



class Maquina:
    def __init__(self, env, tag, tempo_ciclo, capacidade, logger, tempo_setup=10, tempo_limpeza=15):
        self.env = env
        self.tag = tag
        self.tempo_ciclo = tempo_ciclo
        self.capacidade = capacidade
        self.logger = logger
        self.tempo_setup = tempo_setup
        self.tempo_limpeza = tempo_limpeza
        self.maquina = simpy.Resource(env, capacity=1)
        self.lista_status_maquina = []
        self.tempo_ultima_parada = 0
        self.tempo_inicial = 0
        self.produto_atual = None

    

    def set_parada(self, parada):
            self.lista_status_maquina.append(parada) 
            self.logger.registrar_manual(parada.data_inicio,"", parada.tipo,self.tag, f"MANUTENÇÃO")
            self.logger.registrar_manual(parada.data_fim,"", parada.tipo,self.tag, f"MANUTENÇÃO")

    def disponivel(self):
        for parada in self.lista_status_maquina:
            if self.env.now >= parada.data_inicio and self.env.now <= parada.data_fim:
                return False
        return self.maquina.count == 0

    def set_produto(self,produto):
        self.produto_atual = produto

    def set_ultima_parada(self, parada):
        self.tempo_ultima_parada = parada
    
    def processar(self, produto):
        self.logger.registrar(self.env, produto, self.tag, "Início do processamento")
        yield self.env.timeout(self.tempo_ciclo)
        self.logger.registrar(self.env, produto, self.tag, "Fim do processamento")

    def executar_limpeza(self):
        """Método de limpeza da máquina antes da liberação."""
        self.logger.registrar(self.env,"", self.tag, f"Início da limpeza ({self.tempo_limpeza} min)")
        yield self.env.timeout(self.tempo_limpeza)
        self.logger.registrar(self.env, "",self.tag, "Fim da limpeza")

    def adicionar_status(self,status):
        self.lista_status_maquina.append(status)

    def remover_status(self,status):
        self.lista_status_maquina.remove(status)

    def get_tempo_parado(self):
        if self.disponivel():
            return float(self.env.now - self.tempo_ultima_parada)
        return  0

    def get_status_manutenção(self):
        for parada in self.lista_status_maquina:
            if parada.data_inicio > self.env.now and parada.data_fim < self.env.now:
                return True
        return False
    

    def get_tempo_faltante(self):
    # Se não há produto em processamento, a máquina já está livre
        if self.produto_atual is None:
            tempo_fim_parada = 99999
            for parada in self.lista_status_maquina:
                if parada.data_fim > self.env.now and parada.data_inicio < self.env.now:
                    return  parada.data_fim - self.env.now  
          
    # Se há um produto, calcula o tempo total estimado menos o tempo já decorrido
        tempo_total = self.tempo_limpeza + getattr(self.produto_atual, 'digestao_tempo_ciclo', 0.0)
    
    # Exemplo considerando o tempo decorrido no processo atual:
        tempo_decorrido = self.env.now - self.tempo_inicial
        tempo_restante = max(0.0, tempo_total - tempo_decorrido)
    
        return tempo_restante


class Nitrador(Maquina):
    def __init__(self, env, tag, tempo_ciclo, logger, capacidade=10):
        super().__init__(env, tag, tempo_ciclo, capacidade, logger)
        self.qtde_enviada = 0
        self.meta = 0
        self.vazao = 150
        self.evento_acao_necessaria = None
        self.media_vazao = 0
        

    def get_capacidade(self):
        return self.capacidade
    
    def get_qtde_enviada(self, qtde):
        return self.qtde_enviada

    def put_qtde_enviada(self, qtde):
        self.qtde_enviada += qtde

    def reset_qtde_enviada(self):
        self.qtde_enviada = 0
        self.meta = 0

    def set_vazao(self, valor):
        self.vazao = valor

    def get_vazao(self):
        return self.vazao

    def get_nivel_digestor(self):
        try:
            valor = 100 * (self.qtde_enviada / self.meta)
            return valor
        except:
            return 100
    
    def processar(self, qtde_meta, destino_digestor, produto = None):
        self.tempo_inicial = self.env.now
        qtde_restante = qtde_meta
        self.logger.registrar(self.env, produto, "Produção", self.tag, f"Início do enchimento do tanque com {qtde_meta} unidades do produto {destino_digestor.tag}")
        
        while qtde_restante > 0:
            self.evento_acao_necessaria = self.env.event()
            yield self.evento_acao_necessaria
            
            qtde_a_adicionar = min(self.get_vazao(), qtde_restante)
            yield self.env.timeout(1)
            qtde_restante -= qtde_a_adicionar
            self.put_qtde_enviada(qtde_a_adicionar)

        self.reset_qtde_enviada()
        self.tempo_ultima_parada = self.env.now
        vazao = qtde_meta / (self.env.now - self.tempo_inicial)
        self.logger.registrar(self.env, produto, "Produção", self.tag, f"Fim do enchimento do tanque com {qtde_meta} unidades do produto {destino_digestor.tag}", media_vazao = vazao)

    
    def definir_msn(self, escolha_msn = "padrão"):
        self.msn = escolha_msn
        self.logger.registrar(self.env, "", "Produção", self.tag, f"MSN definido para {escolha_msn}")

class Digestor(Maquina):
    def __init__(self, env, tag, tempo_ciclo, logger, capacidade=1100):
        super().__init__(env, tag, tempo_ciclo, capacidade, logger)
        self.nivel_tanque = 0
        self.evento_enchimento_concluido = None

        

    def get_capacidade(self):
        return self.capacidade
        
    def setup(self):
        self.logger.registrar(self.env, "", "Setup", self.tag, "Início do setup do Digestor")
        yield self.env.timeout(self.tempo_setup)
        self.logger.registrar(self.env, "", "Setup", self.tag, "Fim do setup do Digestor")

    def put_qtde_produto(self, qtde):
        qtde_recebida = min(self.capacidade - self.nivel_tanque, qtde)
        self.nivel_tanque += qtde_recebida

    def receber_produto(self, produto):
        self.logger.registrar(self.env, produto, "Recebimento de Produto", self.tag, "Recebendo produto no Digestor")
        self.evento_enchimento_concluido = self.env.event()
        yield self.evento_enchimento_concluido
        self.logger.registrar(self.env, produto, "Recebimento de Produto", self.tag, "Fim do recebimento do produto no Digestor")
        



    def processar(self, produto):
        self.tempo_inicial = self.env.now
        self.produto_atual = produto
        self.logger.registrar(self.env, produto, "Produção", self.tag, "Início do processamento na Digestão")
        yield self.env.timeout(produto.digestao_tempo_ciclo)
        self.logger.registrar(self.env, produto, "Produção", self.tag, "Fim do processamento na Digestão", qtde_produzida= self.capacidade)

    def limpeza_digestor(self):
        self.logger.registrar(self.env, "", "Limpeza digestor", self.tag, "Início da limpeza do Digestor")
        yield self.env.timeout(self.tempo_limpeza)
        self.logger.registrar(self.env, "", "Limpeza digestor", self.tag, "Fim da limpeza do Digestor")
               
class Refinador(Maquina):
    def __init__(self, env, tag, tempo_ciclo, logger, capacidade=1100):
        super().__init__(env, tag, tempo_ciclo, capacidade, logger)

    def processar(self, produto):
        self.logger.registrar(self.env, produto, "Produção", self.tag, "Início do processamento no Refino")
        yield self.env.timeout(self.tempo_ciclo)
        self.logger.registrar(self.env, produto, "Produção", self.tag, "Fim do processamento no Refino")

class Linha:
    def __init__(self, nome, tipos_permitidos, maquinas):
        self.nome = nome
        self.tipos_permitidos = tipos_permitidos  # Ex: ["Tipo_A", "Tipo_B"]
        self.maquinas = maquinas 

    def aceita_produto(self, produto):
        """Verifica se o tipo do produto é compatível com a linha."""
        return produto.tipo in self.tipos_permitidos

class Etapa:
    def __init__(self, env, nome, linhas):
        self.env = env
        self.nome = nome
        self.linhas = linhas

    def selecionar_linha_compativel(self, produto):
        maquinas_validas = []
        for linha in self.linhas:
            if linha.aceita_produto(produto):
                maquinas_validas.extend(linha.maquinas)
        return maquinas_validas
    
    def selecionar_maquina(self, produto):
        maquinas_validas = self.selecionar_linha_compativel(produto)

        # 1. Verifica se há alguma máquina disponível na etapa
        for maquina in maquinas_validas:
            if maquina.disponivel():
                return maquina
        # 2. Se não houver máquina disponível, retorna a com menor fila de espera
        maquina = min(maquinas_validas, key=lambda m: m.get_tempo_faltante())
        if maquina.get_status_manutenção():
            self.env.timeout(maquina.get_tempo_faltante())
        return maquina

    def get_qtde_maquinas_disponiveis(self):
        maquinas = [] 
        for linha in self.linhas:
            maquinas.extend(linha.maquinas)

        qtde = 0

        for maquina in maquinas:
            if maquina.disponivel() == True:
                qtde += 1
        return qtde

    def definir_parada(self, tag,parada):
        maquinas = [] 
        for linha in self.linhas:
            maquinas.extend(linha.maquinas)

        maquina_encontrada = next((m for m in maquinas if m.tag == tag), None)

        if maquina_encontrada:
            maquina_encontrada.set_parada(parada)


class Digestao(Etapa):
    def __init__(self, env, nome, linhas):
        super().__init__(env, nome, linhas)

class Refino(Etapa):
    def __init__(self, env, nome, linhas):
        super().__init__(env, nome, linhas)

class Nitrocelulose:
    def __init__(self, env, nitracao, digestao, plano_entrega,logger):
        self.env = env
        self.nitracao = nitracao
        self.digestao = digestao
        self.plano_entrega = plano_entrega
        self.logger = logger
        self.data_inicio = logger.data_inicio
        
        
    def definir_parada(self,tag,tipo,data_inicio,data_fim):
        parada = status_maquina(tipo,self.logger.obter_sim_time(data_inicio),self.logger.obter_sim_time(data_fim))
        self.digestao.definir_parada(tag,parada)
        

    def gerenciar_processos(self):
        for produto in self.plano_entrega:
            # Dispara o ciclo do produto em paralelo no ambiente de simulação
            self.env.process(self.ciclo_produto(produto))
            # Intervalo entre a entrada de cada produto
            yield self.env.timeout(1)

    def ciclo_produto(self, produto):
        qtde_restante = produto.qtde
        processes_digestores = []
        m_nitrador = self.nitracao.selecionar_maquina(produto)
        req_nitrador = m_nitrador.maquina.request()
        yield req_nitrador
        
        while qtde_restante > 0:


            
            
            m_digestor = self.digestao.selecionar_maquina(produto)
            req_digestor = m_digestor.maquina.request()
            yield req_digestor
            m_digestor.set_produto(produto)

            

            recebimento_digestor = self.env.process(m_digestor.receber_produto(produto))

            yield self.env.process(m_nitrador.processar(qtde_meta= m_digestor.get_capacidade(), destino_digestor=m_digestor, produto=produto))

            m_digestor.evento_enchimento_concluido.succeed()  # Sinaliza que o recebimento foi concluído

            yield recebimento_digestor

            
            qtde_restante -= m_digestor.get_capacidade()
            proc_dig = self.env.process(
                self.ciclo_digestor(m_digestor, req_digestor, produto)
            )
            processes_digestores.append(proc_dig)

            # Assim que a transferência termina, o 'while' recomeça imediatamente,
            # permitindo que o Nitrador pegue o próximo Digestor sem esperar o atual reagir.

        # Aguarda todos os Digestores deste produto terminarem suas reações/limpezas
        
        
        m_nitrador.maquina.release(req_nitrador)
        m_nitrador.set_vazao(0)
        m_nitrador.set_ultima_parada(self.env.now)
        yield self.env.all_of(processes_digestores)
        self.plano_entrega.remove(produto)
        

    def ciclo_digestor(self, digestor, req_digestor, produto):
        yield self.env.process(digestor.processar(produto))
        yield self.env.process(digestor.limpeza_digestor())
        digestor.maquina.release(req_digestor)

