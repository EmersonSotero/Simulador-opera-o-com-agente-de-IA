import tkinter as tk
from tkinter import ttk, messagebox
import pandas as pd
from datetime import datetime

# Integração do Matplotlib com Tkinter
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.dates as mdates


from simulador_gym_rl_v1 import NitroceluloseEnv, Produto
from stable_baselines3 import PPO


# ==========================================
# 1. CONFIGURAÇÕES & CORES
# ==========================================
COR_PRIMARIA = "#1F538D"
COR_FUNDO = "#F5F5F5"

def obter_maquinas():
    return ["DIG-01", "DIG-02",  "DIG-03"]

def obter_produtos_base():
    return ["Lote 01", "Lote 02", "Lote 03", "Lote 04"]

# 1. Catálogo / Tabela de referência com as propriedades padrão dos produtos
CATALOGO_PRODUTOS = {
    "Lote 01": {"tipo": "Tipo_A", "digestao_tempo_ciclo": 60},
    "Lote 02": {"tipo": "Tipo_B", "digestao_tempo_ciclo": 90},
    "Lote 03": {"tipo": "Tipo_A", "digestao_tempo_ciclo": 62},
    "Lote 04": {"tipo": "Tipo_A", "digestao_tempo_ciclo": 58},
}

def construir_plano_entrega(lista_produtos_ui, catalogo=CATALOGO_PRODUTOS):
    """
    Recebe uma lista de dicionários contendo {'nome': ..., 'qtde': ...}
    e cruza com o catálogo para instanciar e retornar os objetos Produto.
    """
    plano_entrega = []
    
    for item in lista_produtos_ui:
        nome = item["nome"]
        qtde = item["qtde"]
        
        # Busca os dados adicionais no catálogo (se não achar, usa valores padrão)
        info_base = catalogo.get(nome, {"tipo": "Desconhecido", "digestao_tempo_ciclo": 60})
        
        # Cria o objeto Produto com a quantidade da UI e as propriedades do catálogo
        produto_instancia = Produto(
            nome=nome,
            qtde=qtde,
            tipo=info_base["tipo"],
            digestao_tempo_ciclo=info_base["digestao_tempo_ciclo"]
        )
        plano_entrega.append(produto_instancia)
        
    return plano_entrega

def rodar_simulacao(produtos, paradas):

    env = NitroceluloseEnv()
    env.adicionar_plano_entrega(construir_plano_entrega(produtos))
    env.definir_parada(paradas[0]['maquina'],paradas[0]['tipo'],paradas[0]['inicio'],paradas[0]['fim'])


    model = PPO.load("ppo_simpy_fabrica")
    obs, info = env.reset()
    done, truncated = False, False

    while not (done or truncated):
        action_model, _ = model.predict(obs, deterministic=True)
        obs, reward, done, truncated, info = env.step(action_model)

    return env.fabrica.logger.obter_dataframe_resumo()
        



# ==========================================
# 2. INTERFACE TKINTER
# ==========================================
class AppSimulador(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Simulador de Sequenciamento")
        self.geometry("900x650")
        self.configure(bg=COR_FUNDO)

        # Dados
        self.paradas = []
        self.produtos = [{"nome": "Lote 01", "qtde": 2200}, {"nome": "Lote 02", "qtde": 3300}]

        # Estrutura de Abas
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=10)

        self.aba_parada = ttk.Frame(self.notebook)
        self.aba_operacao = ttk.Frame(self.notebook)

        self.notebook.add(self.aba_parada, text="Parada")
        self.notebook.add(self.aba_operacao, text="Operação / Produção")

        self._criar_aba_parada()
        self._criar_aba_operacao()

    # --------------------------------------
    # ABA 1: PARADA
    # --------------------------------------
    def _criar_aba_parada(self):
        frame = ttk.LabelFrame(self.aba_parada, text=" Cadastrar Parada ")
        frame.pack(fill="x", padx=10, pady=10)

        # Inputs
        ttk.Label(frame, text="Máquina:").grid(row=0, column=0, padx=5, pady=5)
        self.cb_maquina = ttk.Combobox(frame, values=obter_maquinas(), state="readonly", width=12)
        self.cb_maquina.current(0)
        self.cb_maquina.grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(frame, text="Tipo:").grid(row=0, column=2, padx=5, pady=5)
        self.txt_tipo = ttk.Entry(frame, width=15)
        self.txt_tipo.insert(0, "MANUTENÇÃO")
        self.txt_tipo.grid(row=0, column=3, padx=5, pady=5)

        ttk.Label(frame, text="Início (AAAA-MM-DD HH:MM):").grid(row=1, column=0, padx=5, pady=5)
        self.txt_dt_ini = ttk.Entry(frame, width=18)
        self.txt_dt_ini.insert(0, "2026-09-21 08:00")
        self.txt_dt_ini.grid(row=1, column=1, padx=5, pady=5)

        ttk.Label(frame, text="Fim (AAAA-MM-DD HH:MM):").grid(row=1, column=2, padx=5, pady=5)
        self.txt_dt_fim = ttk.Entry(frame, width=18)
        self.txt_dt_fim.insert(0, "2026-09-21 11:00")
        self.txt_dt_fim.grid(row=1, column=3, padx=5, pady=5)

        btn_add = tk.Button(frame, text="Adicionar Parada", bg=COR_PRIMARIA, fg="white", command=self._add_parada)
        btn_add.grid(row=2, column=0, columnspan=4, pady=10)

        # Lista de Paradas
        ttk.Label(self.aba_parada, text="Paradas Cadastradas:").pack(anchor="w", padx=10)
        self.lst_paradas = tk.Listbox(self.aba_parada, height=12)
        self.lst_paradas.pack(fill="both", expand=True, padx=10, pady=5)

    def _add_parada(self):
        try:
            dt_ini = datetime.strptime(self.txt_dt_ini.get(), "%Y-%m-%d %H:%M")
            dt_fim = datetime.strptime(self.txt_dt_fim.get(), "%Y-%m-%d %H:%M")
            item = {
                "maquina": self.cb_maquina.get(),
                "tipo": self.txt_tipo.get(),
                "inicio": dt_ini,
                "fim": dt_fim
            }
            self.paradas.append(item)
            self.lst_paradas.insert("end", f"{item['maquina']} | {item['tipo']} | {item['inicio']} até {item['fim']}")
        except ValueError:
            messagebox.showerror("Erro", "Formato de data inválido. Use AAAA-MM-DD HH:MM")

    # --------------------------------------
    # ABA 2: OPERAÇÃO & GANTT
    # --------------------------------------
    def _criar_aba_operacao(self):
        f_top = ttk.Frame(self.aba_operacao)
        f_top.pack(fill="x", padx=10, pady=10)

        # Formulário e Lista de Produtos
        ttk.Label(f_top, text="Produto:").pack(side="left", padx=2)
        self.cb_prod = ttk.Combobox(f_top, values=obter_produtos_base(), state="readonly", width=10)
        self.cb_prod.current(0)
        self.cb_prod.pack(side="left", padx=2)

        ttk.Label(f_top, text="Qtd:").pack(side="left", padx=2)
        self.txt_qtd = ttk.Entry(f_top, width=6)
        self.txt_qtd.insert(0, "1000")
        self.txt_qtd.pack(side="left", padx=2)

        btn_add_p = tk.Button(f_top, text="Adicionar", command=self._add_produto)
        btn_add_p.pack(side="left", padx=5)

        # Frame dos produtos adicionados (com botão X)
        self.f_lista_prod = ttk.Frame(self.aba_operacao)
        self.f_lista_prod.pack(fill="x", padx=10)

        # Botão Simular Destaque
        btn_simular = tk.Button(f_top, text="SIMULAR", bg="green", fg="white", font=("Arial", 10, "bold"), command=self._simular)
        btn_simular.pack(side="right", padx=10)

        # Área reservada para o Gráfico Matplotlib
        self.f_gantt = ttk.Frame(self.aba_operacao)
        self.f_gantt.pack(fill="both", expand=True, padx=10, pady=10)

        self._atualizar_produtos_ui()

    def _add_produto(self):
        try:
            qtd = int(self.txt_qtd.get())
            self.produtos.append({"nome": self.cb_prod.get(), "qtde": qtd})
            self._atualizar_produtos_ui()
        except ValueError:
            pass

    def _remover_produto(self, idx):
        self.produtos.pop(idx)
        self._atualizar_produtos_ui()

    def _atualizar_produtos_ui(self):
        for w in self.f_lista_prod.winfo_children():
            w.destroy()

        for idx, p in enumerate(self.produtos):
            f_item = ttk.Frame(self.f_lista_prod)
            f_item.pack(side="left", padx=5, pady=2)
            
            lbl = ttk.Label(f_item, text=f"{p['nome']} ({p['qtde']})")
            lbl.pack(side="left")

            btn_del = tk.Button(f_item, text="X", fg="red", bd=0, command=lambda i=idx: self._remover_produto(i))
            btn_del.pack(side="left", padx=2)

    def _simular(self):
        df = rodar_simulacao(self.produtos, self.paradas)
        self._desenhar_gantt(df)

    def _desenhar_gantt(self, df):
        # Limpa gráfico anterior se existir
        for w in self.f_gantt.winfo_children():
            w.destroy()

        df['data_hora_inicio'] = pd.to_datetime(df['data_hora_inicio'])
        df['data_hora_fim'] = pd.to_datetime(df['data_hora_fim'])

        fig, ax = plt.subplots(figsize=(8, 3.5), dpi=100)

        maquinas = list(df['componente'].unique())
        cores = {'PRODUÇÃO': '#2b5c8f', 'MANUTENÇÃO': '#d9534f'}

        for _, row in df.iterrows():
            y_pos = maquinas.index(row['componente'])
            inicio = mdates.date2num(row['data_hora_inicio'])
            fim = mdates.date2num(row['data_hora_fim'])
            duracao = fim - inicio

            cor = cores.get(row['tipo_acao'], '#6c757d')
            ax.barh(y_pos, duracao, left=inicio, align='center', color=cor, edgecolor='black', alpha=0.85)
            
            # Texto do produto dentro da barra
            ax.text(inicio + duracao/2, y_pos, row['produto'], ha='center', va='center', color='white', fontsize=8, fontweight='bold')

        ax.set_yticks(range(len(maquinas)))
        ax.set_yticklabels(maquinas)
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
        ax.set_title("Gráfico de Gantt - Sequenciamento")
        fig.tight_layout()

        # Insere o gráfico nativamente dentro da janela Tkinter
        canvas = FigureCanvasTkAgg(fig, master=self.f_gantt)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)


if __name__ == "__main__":
    app = AppSimulador()
    app.mainloop()