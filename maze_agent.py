import sys
import os
import random
import time
import cv2
import numpy as np
from datetime import datetime


# CLASSE PARA GRAVAÇÃO DE VÍDEO
class VideoRecorder:
    def __init__(self, filename="maze_execution.mp4", fps=5.0, cell_size=30):
        self.filename = filename
        self.fps = fps
        self.cell_size = cell_size
        self.video_writer = None
        self.frame_width = 0
        self.frame_height = 0
        
        # Cores para diferentes elementos (BGR format)
        self.colors = {
            'X': (50, 50, 50),      # Parede - cinza escuro
            '_': (255, 255, 255),   # Corredor - branco
            'o': (0, 255, 255),     # Comida - amarelo
            'S': (0, 255, 0),       # Saída - verde
            'A': (0, 0, 255),       # Agente - vermelho
            'E': (255, 255, 255),   # Entrada - branco (mesmo que corredor)
        }
    
    def setup_video(self, maze_rows, maze_cols):
        """Configura o gravador de vídeo com dimensões do labirinto"""
        self.frame_width = maze_cols * self.cell_size
        self.frame_height = maze_rows * self.cell_size * 2
        
        # Define codec e cria VideoWriter
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        self.video_writer = cv2.VideoWriter(
            self.filename, fourcc, self.fps, 
            (self.frame_width, self.frame_height)
        )
        
        if not self.video_writer.isOpened():
            print(f"Erro: Não foi possível abrir o arquivo de vídeo {self.filename}")
            return False
        
        print(f"Gravação iniciada: {self.filename} ({self.frame_width}x{self.frame_height})")
        return True
    
    def create_frame(self, labirinto, agent_row, agent_col, step_info=""):
        """Cria um frame do labirinto atual"""
        if self.video_writer is None:
            return None
        
        # Cria imagem em branco
        frame = np.zeros((self.frame_height, self.frame_width, 3), dtype=np.uint8)
        
        # Desenha cada célula do labirinto
        for i in range(len(labirinto)):
            for j in range(len(labirinto[i])):
                # Calcula posição do pixel
                y1 = i * self.cell_size
                x1 = j * self.cell_size
                y2 = (i + 1) * self.cell_size
                x2 = (j + 1) * self.cell_size
                            
                cell_content = labirinto[i][j]
                           
                if i == agent_row and j == agent_col:
                    color = self.colors['A']
                else:
                    color = self.colors.get(cell_content, (128, 128, 128))  # Cinza padrão
                             
                cv2.rectangle(frame, (x1, y1), (x2-1, y2-1), color, -1)
                
                cv2.rectangle(frame, (x1, y1), (x2-1, y2-1), (0, 0, 0), 1) # borda preta fina 
        
        # Adiciona texto com informações do passo (opcional)
        if step_info:
            cv2.putText(frame, step_info, (10, 25), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        return frame
    
    def add_frame(self, labirinto, agent_row, agent_col, step_info=""):
        """Adiciona um frame ao vídeo"""
        frame = self.create_frame(labirinto, agent_row, agent_col, step_info)
        if frame is not None:
            self.video_writer.write(frame)
    
    def finalize(self):
        """Finaliza gravação do vídeo"""
        if self.video_writer:
            self.video_writer.release()
            print(f"Vídeo salvo como: {self.filename}")


# DEFINIÇÃO DO AMBIENTE 
class Ambiente:
    def __init__(self, nome_arquivo, video_recorder=None):
        self.labirinto = []
        self.linha_agente = 0
        self.coluna_agente = 0
        self.direcao_agente = 'N'
        self.linhas = 0
        self.colunas = 0
        self.total_comida = 0
        self.comida_restante = 0
        self.video_recorder = video_recorder

        self.carregar_labirinto(nome_arquivo)
        self.encontrar_posicao_agente()
        self.contar_comida()
        
        # Configura gravador de vídeo se fornecido
        if self.video_recorder:
            self.video_recorder.setup_video(self.linhas, self.colunas)

    def carregar_labirinto(self, nome_arquivo):
        """Carrega labirinto do arquivo de texto"""
        with open(nome_arquivo, 'r') as arquivo:
            linhas = arquivo.read().strip().split('\n')

        # Normaliza comprimento de linhas (se houver variação) - pega o maior
        self.linhas = len(linhas)
        self.colunas = max(len(l) for l in linhas) if linhas else 0

        # Preenche cada linha para o mesmo tamanho (com X se faltar)
        self.labirinto = [list(l.ljust(self.colunas, 'X')) for l in linhas]

    def encontrar_posicao_agente(self):
        """Encontra posição inicial do agente (E)"""
        for i in range(self.linhas):
            for j in range(self.colunas):
                if self.labirinto[i][j] == 'E':
                    self.linha_agente = i
                    self.coluna_agente = j
                    self.direcao_agente = 'N'  # Direção padrão
                    self.labirinto[i][j] = '_'  # Substitui entrada por corredor
                    return

    def contar_comida(self):
        """Conta total de comida no labirinto"""
        self.total_comida = 0
        for i in range(self.linhas):
            for j in range(self.colunas):
                if self.labirinto[i][j] == 'o':
                    self.total_comida += 1
        self.comida_restante = self.total_comida

    def obter_sensor(self):
        """Retorna matriz 3x3 do sensor ao redor do agente"""
        sensor = [['X' for _ in range(3)] for _ in range(3)]

        # Obtém área 3x3 ao redor do agente
        for i in range(3):
            for j in range(3):
                linha = self.linha_agente - 1 + i
                coluna = self.coluna_agente - 1 + j

                # Verifica limites
                if linha < 0 or linha >= self.linhas or coluna < 0 or coluna >= self.colunas:
                    sensor[i][j] = 'X'  # Parede para fora dos limites
                else:
                    sensor[i][j] = self.labirinto[linha][coluna]

        # Define direção do agente no centro (1,1)
        sensor[1][1] = self.direcao_agente

        return sensor

    def definir_direcao(self, direcao):
        """Define direção do agente"""
        self.direcao_agente = direcao

    def mover(self):
        """Move agente na direção atual"""
        nova_linha = self.linha_agente
        nova_coluna = self.coluna_agente

        # Calcula nova posição baseada na direção
        if self.direcao_agente == 'N':
            nova_linha -= 1
        elif self.direcao_agente == 'S':
            nova_linha += 1
        elif self.direcao_agente == 'L':
            nova_coluna += 1
        elif self.direcao_agente == 'O':
            nova_coluna -= 1

        # Verifica se movimento é válido
        if (0 <= nova_linha < self.linhas and 0 <= nova_coluna < self.colunas and
                self.labirinto[nova_linha][nova_coluna] != 'X'):

            # Verifica se há comida na nova posição
            if self.labirinto[nova_linha][nova_coluna] == 'o':
                self.comida_restante -= 1
                self.labirinto[nova_linha][nova_coluna] = '_'  # Come a comida

            self.linha_agente = nova_linha
            self.coluna_agente = nova_coluna
            return True

        return False  # Movimento inválido

    def esta_na_saida(self):
        """Verifica se agente está na saída"""
        return self.labirinto[self.linha_agente][self.coluna_agente] == 'S'

    def toda_comida_coletada(self):
        """Verifica se toda comida foi coletada"""
        return self.comida_restante == 0

    def obter_total_comida(self):
        """Obtém contagem total de comida"""
        return self.total_comida

    def obter_comida_restante(self):
        """Obtém contagem de comida restante"""
        return self.comida_restante

    def imprimir_labirinto(self, step_info=""):
        """Imprime estado atual do labirinto com posição do agente (com flush)"""
        linhas = []
        for i in range(self.linhas):
            linha_chars = []
            for j in range(self.colunas):
                if i == self.linha_agente and j == self.coluna_agente:
                    linha_chars.append('A')  # Mostra posição do agente
                else:
                    linha_chars.append(self.labirinto[i][j])
            linhas.append(''.join(linha_chars))
        # Imprime tudo de uma vez e força flush para evitar buffering
        print('\n'.join(linhas), flush=True)
        print(flush=True)
        
        # Adiciona frame ao vídeo se gravador estiver ativo
        if self.video_recorder:
            self.video_recorder.add_frame(
                self.labirinto, 
                self.linha_agente, 
                self.coluna_agente, 
                step_info
            )


# DEFINIÇÃO DO AGENTE (modificada para incluir memória da saída)
class Agente:
    def __init__(self, ambiente, comida_esperada):
        self.ambiente = ambiente
        self.comida_esperada = comida_esperada
        self.passos = 0                # Contador de movimentos
        self.comida_coletada = 0
        self.posicoes_visitadas = set()
        self.direcoes = ['N', 'L', 'S', 'O']  # Norte, Leste, Sul, Oeste
        self.modo_detalhado = True  # Controla nível de detalhes e pausas pra melhor impressão no console

        # Sistema de memória
        self.mapa_conhecido = {}  # (linha, coluna): 'X', '_', 'o', 'S'
        self.contador_visitas = {}  # (linha, coluna): número de vezes visitado
        self.locais_comida = set()  # Posições conhecidas de comida
        self.posicoes_exploradas = set()  # Posições exploradas
        
        # NOVA FUNCIONALIDADE: Memória da saída
        self.posicao_saida = None  # Armazena posição da saída quando encontrada
        self.saida_conhecida = False  # Flag indicando se a saída foi encontrada

        # Contador de iterações
        self.iteracoes = 0

    def executar(self):
        """Loop principal de execução do agente (imprime passo-a-passo desde o início)"""
        print("Agente iniciou exploração!", flush=True)
        print("Passo 0 (inicial):", flush=True)
        
        step_info = f"Inicio - Comida: {self.comida_coletada}/{self.comida_esperada}"
        self.ambiente.imprimir_labirinto(step_info)

        # Continua até que TODA comida tenha sido coletada E o agente esteja na saída
        while not (self.ambiente.toda_comida_coletada() and self.ambiente.esta_na_saida()):
            self.iteracoes += 1

            sensor = self.ambiente.obter_sensor()

            # Atualiza mapa interno com dados do sensor
            self.atualizar_memoria(sensor)

            # Estratégia: tentar mover em direção à comida ou áreas não exploradas
            proxima_direcao = self.decidir_proximo_movimento(sensor)
            self.ambiente.definir_direcao(proxima_direcao)

            # Mostra a tentativa antes de executar o movimento (ajuda a acompanhar passo-a-passo)
            print(f"Iteração {self.iteracoes} — Tentativa de mover: {proxima_direcao} (Passos efetivos: {self.passos})", flush=True)

            moveu = self.ambiente.mover()

            if moveu:
                self.passos += 1

                # Rastreia posição atual
                posicao_atual = self.obter_posicao_atual()
                self.contador_visitas[posicao_atual] = self.contador_visitas.get(posicao_atual, 0) + 1

                # NOVA FUNCIONALIDADE: Verifica se passou pela saída
                if self.ambiente.esta_na_saida() and not self.saida_conhecida:
                    self.posicao_saida = posicao_atual
                    self.saida_conhecida = True
                    print(f"🎯 SAÍDA ENCONTRADA e memorizada na posição: {posicao_atual}!", flush=True)

                # Verifica se comida foi coletada
                comida_restante_atual = self.ambiente.obter_comida_restante()
                comida_coletada_atual = self.comida_esperada - comida_restante_atual
                if comida_coletada_atual > self.comida_coletada:
                    self.comida_coletada = comida_coletada_atual
                    print(f"Comida coletada! Total: {self.comida_coletada}", flush=True)
                    # Remove comida da memória já que foi coletada
                    if posicao_atual in self.locais_comida:
                        self.locais_comida.remove(posicao_atual)

            else:
                print("Movimento bloqueado (parede/limite).", flush=True)

            # Imprime o labirinto a cada iteração (assim você verá passo a passo)
            print(f"-- Estado após iteração {self.iteracoes} (passos efetivos: {self.passos}) --", flush=True)
            
            # Cria informação para o frame do vídeo
            saida_info = " | Saída: Memorizada" if self.saida_conhecida else " | Saída: Procurando"
            step_info = f"Iter: {self.iteracoes} | Passos: {self.passos} | Comida: {self.comida_coletada}/{self.comida_esperada}{saida_info}"
            self.ambiente.imprimir_labirinto(step_info)

            # Pequena pausa quando em modo detalhado, para facilitar leitura humana
            if self.modo_detalhado:
                time.sleep(0.05)

            # Previne loops infinitos: limite de iterações
            if self.iteracoes > 20000:
                print("Número máximo de iterações atingido! Interrompendo.", flush=True)
                break

        self.imprimir_resultados_finais()

    def atualizar_memoria(self, sensor):
        """Atualiza mapa interno baseado nos dados do sensor"""
        posicao_atual = self.obter_posicao_atual()

        # Atualiza conhecimento da área circundante
        for i in range(3):
            for j in range(3):
                # Calcula posição real no labirinto
                linha = posicao_atual[0] + (i - 1)
                coluna = posicao_atual[1] + (j - 1)
                pos = (linha, coluna)

                # Pula posição central (posição do agente)
                if i == 1 and j == 1:
                    continue

                conteudo_celula = sensor[i][j]

                # Atualiza nosso mapa
                self.mapa_conhecido[pos] = conteudo_celula

                # Rastreia locais de comida
                if conteudo_celula == 'o':
                    self.locais_comida.add(pos)
                elif pos in self.locais_comida and conteudo_celula != 'o':
                    # Comida foi coletada, remove dos locais conhecidos
                    self.locais_comida.remove(pos)
                
                # NOVA FUNCIONALIDADE: Memoriza posição da saída se encontrada no sensor
                if conteudo_celula == 'S' and not self.saida_conhecida:
                    self.posicao_saida = pos
                    self.saida_conhecida = True
                    print(f"🎯 SAÍDA DETECTADA pelo sensor na posição: {pos}!", flush=True)

    def obter_posicao_atual(self):
        """Obtém posição atual do agente do ambiente"""
        return (self.ambiente.linha_agente, self.ambiente.coluna_agente)

    def decidir_proximo_movimento(self, sensor):
        """Decide próximo movimento baseado no sensor e memória"""
        direcao_atual = sensor[1][1]
        posicao_atual = self.obter_posicao_atual()

        # Prioridade 1: Procurar comida em células adjacentes
        direcoes_comida = []
        if sensor[0][1] == 'o':  # Norte
            direcoes_comida.append('N')
        if sensor[1][2] == 'o':  # Leste
            direcoes_comida.append('L')
        if sensor[2][1] == 'o':  # Sul
            direcoes_comida.append('S')
        if sensor[1][0] == 'o':  # Oeste
            direcoes_comida.append('O')

        if direcoes_comida:
            return direcoes_comida[0]  # Vai para primeira comida disponível

        # Prioridade 2: Se toda comida coletada, ir para saída
        if self.ambiente.toda_comida_coletada():
            # FUNCIONALIDADE MELHORADA: Usa saída memorizada se disponível
            if self.saida_conhecida and self.posicao_saida:
                print("🏃‍♂️ Toda comida coletada! Dirigindo-se à saída memorizada...", flush=True)
                melhor_direcao = self.encontrar_direcao_para_posicao_alvo(posicao_atual, self.posicao_saida)
                if melhor_direcao and self.pode_mover_na_direcao(sensor, melhor_direcao):
                    return melhor_direcao
            
            # Fallback: procura saída adjacente se não conseguir usar a memorizada
            direcoes_saida = []
            if sensor[0][1] == 'S':
                direcoes_saida.append('N')
            if sensor[1][2] == 'S':
                direcoes_saida.append('L')
            if sensor[2][1] == 'S':
                direcoes_saida.append('S')
            if sensor[1][0] == 'S':
                direcoes_saida.append('O')

            if direcoes_saida:
                return direcoes_saida[0]

        # Prioridade 3: Mover em direção aos locais conhecidos de comida
        if self.locais_comida:
            melhor_direcao = self.encontrar_direcao_para_comida_mais_proxima(posicao_atual)
            if melhor_direcao and self.pode_mover_na_direcao(sensor, melhor_direcao):
                return melhor_direcao

        # Prioridade 4: Explorar áreas não visitadas (evita posições muito visitadas)
        direcoes_disponiveis = []
        posicoes_direcoes = {
            'N': (posicao_atual[0] - 1, posicao_atual[1]),
            'L': (posicao_atual[0], posicao_atual[1] + 1),
            'S': (posicao_atual[0] + 1, posicao_atual[1]),
            'O': (posicao_atual[0], posicao_atual[1] - 1)
        }

        for direcao, proxima_pos in posicoes_direcoes.items():
            if self.pode_mover_na_direcao(sensor, direcao):
                contador_visitas = self.contador_visitas.get(proxima_pos, 0)
                direcoes_disponiveis.append((direcao, contador_visitas))

        if direcoes_disponiveis:
            # Ordena por contador de visitas (prefere posições menos visitadas)
            direcoes_disponiveis.sort(key=lambda x: x[1])
            return direcoes_disponiveis[0][0]

        # Prioridade 5: Continuar na direção atual se possível (a ideia é garantir que o agente irá percorrer toda a linha antes de descer/subir);
        if self.pode_mover_na_direcao(sensor, direcao_atual):
            return direcao_atual

        # Último recurso: direção válida aleatória (afim de garantir uma movimentação)
        direcoes_validas = []
        if sensor[0][1] != 'X':
            direcoes_validas.append('N')
        if sensor[1][2] != 'X':
            direcoes_validas.append('L')
        if sensor[2][1] != 'X':
            direcoes_validas.append('S')
        if sensor[1][0] != 'X':
            direcoes_validas.append('O')

        if direcoes_validas:
            return random.choice(direcoes_validas)

        return direcao_atual  # Travado, tenta direção atual

    def encontrar_direcao_para_comida_mais_proxima(self, posicao_atual):
        """Encontra direção geral para comida conhecida mais próxima"""
        if not self.locais_comida:
            return None

        # Encontra comida mais próxima
        comida_mais_proxima = min(self.locais_comida,
                                  key=lambda pos: abs(pos[0] - posicao_atual[0]) + abs(pos[1] - posicao_atual[1]))

        return self.encontrar_direcao_para_posicao_alvo(posicao_atual, comida_mais_proxima)

    def encontrar_direcao_para_posicao_alvo(self, posicao_atual, posicao_alvo):
        """NOVA FUNÇÃO: Encontra direção geral para uma posição alvo específica"""
        diferenca_linha = posicao_alvo[0] - posicao_atual[0]
        diferenca_coluna = posicao_alvo[1] - posicao_atual[1]

        # Prefere movimento horizontal ou vertical em direção ao alvo
        if abs(diferenca_linha) > abs(diferenca_coluna):
            return 'S' if diferenca_linha > 0 else 'N'
        elif diferenca_coluna != 0:
            return 'L' if diferenca_coluna > 0 else 'O'

        return None

    def pode_mover_na_direcao(self, sensor, direcao):
        """Verifica se agente pode mover na direção dada"""
        mapa_direcoes = {
            'N': sensor[0][1],
            'L': sensor[1][2],
            'S': sensor[2][1],
            'O': sensor[1][0]
        }
        return mapa_direcoes.get(direcao, 'X') != 'X'

    def adicionar_posicao_atual_aos_visitados(self):
        """Adiciona posição atual ao conjunto de visitados"""
        posicao_atual = self.obter_posicao_atual()
        self.posicoes_visitadas.add(posicao_atual)

    def imprimir_resultados_finais(self):
        """Imprime resultados finais e pontuação"""
        print("\n=== RESULTADOS FINAIS ===", flush=True)
        print(f"Passos dados: {self.passos}", flush=True)
        print(f"Comida coletada: {self.comida_coletada}", flush=True)
        print(f"Comida esperada: {self.comida_esperada}", flush=True)
        
        # NOVA INFO: Status da saída
        if self.saida_conhecida:
            print(f"Saída memorizada na posição: {self.posicao_saida}", flush=True)
        else:
            print("Saída não foi encontrada durante a exploração", flush=True)

        pontos_comida = self.comida_coletada * 10
        penalidade_passos = self.passos * 1
        pontuacao_total = pontos_comida - penalidade_passos

        print("\n=== PONTUAÇÃO ===", flush=True)
        print(f"Pontos por comida (10 por comida): {pontos_comida}", flush=True)
        print(f"Penalidade por passos (-1 por passo): -{penalidade_passos}", flush=True)
        print(f"PONTUAÇÃO TOTAL: {pontuacao_total}", flush=True)

        if self.ambiente.toda_comida_coletada() and self.ambiente.esta_na_saida():
            print("✅ SUCESSO: Toda comida coletada e chegou na saída!", flush=True)
        elif self.ambiente.toda_comida_coletada():
            print("⚠️ Sucesso parcial: Toda comida coletada mas não chegou na saída", flush=True)
        else:
            restante = self.ambiente.obter_comida_restante()
            print(f"❌ Missão incompleta: {restante} comida restante", flush=True)


def criar_labirinto_exemplo():
    """Cria um arquivo de labirinto exemplo para teste"""
    labirinto_exemplo = """XXXXXXXXX
XE______X
X_XXXX_oX
X______XX
XXX_X___X
X_o___X_X
X_XXX_X_X
X_____o_X
XXXXXXSXX"""

    with open("labirinto.txt", "w") as f:
        f.write(labirinto_exemplo)


def main():
    try:
        # Verifica se nome do arquivo foi fornecido como argumento
        nome_arquivo = "labirinto.txt"
        modo_detalhado = True
        gravar_video = True  # Novo parâmetro para controlar gravação
        nome_video = f"maze_execution_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"

        if len(sys.argv) > 1:
            nome_arquivo = sys.argv[1]
        if len(sys.argv) > 2 and sys.argv[2] == "simples":
            modo_detalhado = False
        if len(sys.argv) > 3 and sys.argv[3] == "no-video":
            gravar_video = False
        if len(sys.argv) > 4:
            nome_video = sys.argv[4]

        print(f"Carregando labirinto de: {nome_arquivo}", flush=True)

        # Verifica se arquivo existe
        if not os.path.exists(nome_arquivo):
            print(f"Erro: Arquivo '{nome_arquivo}' não encontrado!", flush=True)
            print(f"\nCriando arquivo de exemplo labirinto.txt...", flush=True)
            criar_labirinto_exemplo()
            print("Arquivo labirinto.txt criado! Execute o programa novamente.", flush=True)
            return

        # Cria gravador de vídeo se solicitado
        video_recorder = None
        if gravar_video:
            try:
                video_recorder = VideoRecorder(nome_video, fps=5.0, cell_size=40)
                print(f"Gravação de vídeo ativada: {nome_video}", flush=True)
            except ImportError:
                print("OpenCV não encontrado. Gravação de vídeo desabilitada.", flush=True)
                print("Para instalar: pip install opencv-python", flush=True)
                video_recorder = None

        # Cria ambiente
        ambiente = Ambiente(nome_arquivo, video_recorder)

        # Obtém contagem total de comida
        total_comida = ambiente.obter_total_comida()
        print(f"Total de comida no labirinto: {total_comida}", flush=True)

        # Cria e executa agente
        agente = Agente(ambiente, total_comida)
        agente.modo_detalhado = modo_detalhado
        agente.executar()

        # Finaliza gravação de vídeo
        if video_recorder:
            video_recorder.finalize()
            print(f"\n✅ Vídeo da execução salvo como: {nome_video}")

    except FileNotFoundError:
        print(f"Erro: Não foi possível encontrar o arquivo do labirinto", flush=True)
        print("\nFormato do arquivo labirinto.txt:", flush=True)
        print("XXXXXXX", flush=True)
        print("XE__o_X", flush=True)
        print("X_X_X_X", flush=True)
        print("X_o___X", flush=True)
        print("X_X_XSX", flush=True)
        print("XXXXXXX", flush=True)
        print("\nOnde:", flush=True)
        print("X = parede", flush=True)
        print("_ = corredor", flush=True)
        print("o = comida", flush=True)
        print("E = entrada (início do agente)", flush=True)
        print("S = saída", flush=True)
        print("\nUso: python programa.py [arquivo] [simples]", flush=True)
        print("  simples = modo menos detalhado", flush=True)

    except Exception as e:
        print(f"Erro inesperado: {e}", flush=True)
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
