class Processador:

    def __init__(self, memoria_cache):
        """ Recebe uma cache com acesso a memória principal. 
            Isso me garante que dentro da CPU tem "apenas" a CACHE.

            Para acessar a principal seria: cache.memoria_principal. ... 
        """
        self.cache = memoria_cache


        # Registradores
        self.registradores = [0] * 32
        self.registradores[29] = self.cache.ram.pilha_fim  # $sp no topo da pilha
        self.PC = self.cache.ram.text_inicio  # Começa no início da seção text


        # Estruturas de dados que vai transitar entre os estágios.

        self.IF_ID = {
            'instruction': 0,      # Instrução de 32 bits
            'PC': 0,               # Endereço desta instrução
            'PC_mais_4': 0,        # PC + 4 (para branches)
            'valid': False         # Tem instrução válida?
        }


        self.ID_EX = {
            # Campos para as instruções.
            'opcode': 0,            
            'rs': 0,                
            'rt': 0,                
            'rd': 0,                
            'shamt': 0,             
            'funct': 0,             
            'immediate': 0,         
            'immediate_signed': 0,  
            'address': 0,           
            
            # Conjunto de informação semanticas para 
            # identificação do tipo de instrução
            'tipo': 'unknown',     # 'R', 'I', 'branch', 'jump', 'unknown'
            'subtipo': 'unknown',  # 'add', 'lw', 'beq', 'j', etc.
            'descricao': '',       # Descrição humana: "ADD R-type", "Load Word", etc.
            
            # Campo para os dados lidos dos registradores.
            'dado1': 0,       # Valor do registrador rs
            'dado2': 0,       # Valor do registrador rt
            
            # Sinais de controle || Vai ser propagada para o EX_MEM
            'PC_mais_4': 0,        # PC + 4 (para branches e jumps)
            'controle': {          # Sinais de controle da unidade principal
                'RegWrite': 0, 'RegDst': 0, 'ALUSrc': 0, 'MemToReg': 0,
                'MemRead': 0, 'MemWrite': 0, 'Branch': 0, 'ALUOp': 0
            },
            
            # Metadados
            'PC_origem': 0,        # PC onde esta instrução foi buscada (para debug)
            'valid': False         # Indica se os dados são válidos
        }


        self.EX_MEM = {

            # Dados processados
            'ALU_result': 0,         # Resultado da ULA
            'write_data': 0,         # Dado para stores (valor do registrador rt ?)
            'write_reg': 0,          # Registrador destino (rt ou rd ?)


            # Sinais de controle
            'MemRead': False,       # É instrução de load? lw
            'MemWrite': False,      # É instrução de store? sw
            'RegWrite': False,      # Escreve no banco de registradores?
            'MemToReg': False,      # Dado veio da memoria ou da ULA
            'Branch': False,        # É instrução de branch?
            'branch_taken': False,  # A branch aconteceu?  ??
            'branch_target': 0,     # Alvo do branch (se taken)
            
            'valid': False
        }

        self.MEM_WB = {
            'write_data': 0,         # Dado para write back
            'write_reg': 0,          # Registrador destino
            'RegWrite': False,       # Controla write back
            'MemToReg': False,       # Veio da ULA? para debug.

            'valid': False
        }


        # Controle de execução

        self.ciclo = 0
        self.rodando = True
        self.instrucoes_executadas = 0

        # Controle de hazards

        self.stall_IF = False
        self.stall_ID = False


    # Função auxiliar para verificar hazard de dados (Load-Use)
    def _verificar_conflito_memoria(self, rs, rt):
        # Se a instrução anterior (que ta indo pro MEM) for um Load
        # E ela vai escrever no registrador que a gente precisa agora...
        if self.EX_MEM['valid'] and self.EX_MEM['MemRead']:
            load_reg = self.EX_MEM['write_reg']
            if load_reg != 0:
                if load_reg == rs or load_reg == rt:
                    return True # Tem conflito, precisa de Stall
        return False


    def IF_stage(self):
        """
            Responsável por buscar da memória e atualiza os dados para serem 
            transitados entre os estágios.
        """

        # Controle de execução do IF_stage
        if not self.rodando:
            self.IF_ID['valid'] = False
            return


        # Deteção de fim de programa.
        fim_do_programa = self.cache.ram.text_inicio + (60 * 4) # Aumentei um pouco a margem
        if self.PC >= fim_do_programa:
            self.rodando = False
            # print("\n Fim do programa alcancado! \n")
            return


        # Detecção de hazard - pausa o fetch
        if self.stall_IF:
            # self.IF_ID['valid'] = False # Não invalida, só segura
            # print("IF: Stall - fetch pausado")
            return


        # Verifica se não está estourando a memória fisica ou fora da memória fisica.
        if self.PC >= len(self.cache.ram.dados) - 3:
            self.rodando = False
            self.IF_ID['valid'] = False
            print(F"IF: Erro {hex(self.PC)} fora da memória fisica")
            return

        # Busca da instrução. 
        # arrumar acesso a memoria.

        try: # Tenta acesso na Cache

                instrucao = self.cache.ler_palavra(self.PC)
                
                # Checagem de segurança pra ver se não é lixo de memória
                if instrucao == 0xFFFFFFFF: 
                    self.rodando = False
                    self.IF_ID['valid'] = False
                    return

        except Exception as cache_error:

            try:
                 
                instrucao = self.cache.ram.ler_palavra(self.PC)
            
            except Exception as ram_error:

                # print(f"IF: Cache falhou em {hex(self.PC)}: {cache_error}")
                self.rodando = False
                self.IF_ID['valid'] = False
                return


        # Preenchendo a estrutura de dados.

        self.IF_ID['instruction'] = instrucao
        self.IF_ID['PC'] = self.PC
        self.IF_ID['PC_mais_4'] = self.PC + 4 # Estágio "atual"
        self.IF_ID['valid'] = True

        # Atualiza a PC de forma global
        self.PC += 4 # Assume que não é branch por padrão.




    def _detectar_tipo_instrucao(self, opcode, funct):
        """ 
            Sub função do estágio ID para detecta o tipo 
            e subtipo da instrução 
        """

         
        # Constantes para melhor legibilidade
        R_TYPE = 0x00
        ADDI = 0x08
        LW = 0x23
        SW = 0x2B 
        BEQ = 0x04 
        BNE = 0x05 
        J = 0x02 
        JAL = 0x03
        

        if opcode == R_TYPE:
           # Detecta subtipo R pela função
            subtipos_r = {
                0x20: 'add', 0x22: 'sub', 0x24: 'and', 0x25: 'or',
                0x2A: 'slt', 0x00: 'sll', 0x02: 'srl'
            }
            
            return {
                'type': 'R',
                'subtype': subtipos_r.get(funct, 'unknown'),
                'descricao': f"R-type: {subtipos_r.get(funct, 'unknown')}"
            }
        
        elif opcode in [LW, SW, ADDI]:
            subtipos_i = {LW: 'lw', SW: 'sw', ADDI: 'addi'}
            return {
                'type': 'I', 
                'subtype': subtipos_i[opcode],
                'descricao': f"I-type: {subtipos_i[opcode]}"
            }
        
        elif opcode in [BEQ, BNE]:
            subtipos_branch = {BEQ: 'beq', BNE: 'bne'}
            return {
                'type': 'branch',
                'subtype': subtipos_branch[opcode],
                'descricao': f"Branch: {subtipos_branch[opcode]}"
            }
        
        elif opcode in [J, JAL]:
            return {
                'type': 'jump',
                'subtype': 'j' if opcode == J else 'jal',
                'descricao': 'Jump' if opcode == J else 'Jump and Link'
            }
        
        else:
            return {
                'type': 'unknown',
                'subtype': 'unknown',
                'descricao': f"Instrução desconhecida (opcode: {opcode:02x})"
        }



    def _mapear_funct_para_alu(self, funct_subtipo):
        """
            Sub-função auxiliar da mapear 
            responsável por Mapear subtipo R para operação ALU
        """

        mapeamento = {
                'add': 'ADD', 'sub': 'SUB', 'and': 'AND', 'or': 'OR',
                'slt': 'SLT', 'sll': 'SLL', 'srl': 'SRL', 'nor': 'NOR'
        }

        return mapeamento.get(funct_subtipo, 'ADD')



    # Verificar inconssistencias no EX, ori? OR? slti? 
    def _mapear_opcode_para_alu(self, opcode_subtipo):
        """
            Mapeia subtipo I para operação ALU
        """

        mapeamento = {
            'addi': 'ADD', 'andi': 'AND', 'ori': 'OR', 'slti': 'SLT'
        }

        return mapeamento.get(opcode_subtipo, 'ADD')


            

        # O cerébro do processador
    def _gerar_sinais_controle(self, info_tipo):
        """
            Gera os sinais de controle baseado no tipo/subtipo da instrução
            Retorna um dicionário com todos os sinais
        """

        # Constantes para os sinais
        SIM = 1
        NAO = 0

        REG_DST_RD = 1    # Registrador destino é rd
        REG_DST_RT = 0    # Registrador destino é rt

        ALU_SRC_REG = 0   # Fonte ALU é registrador
        ALU_SRC_IMM = 1   # Fonte ALU é immediate

        MEM_TO_REG_ALU = 0  # Dado vem da ALU
        MEM_TO_REG_MEM = 1  # Dado vem da memória

        ALU_OP_ADD = 0     # ALU faz ADD
        ALU_OP_SUB = 1     # ALU faz SUB
        ALU_OP_FUNCT = 2   # ALU opera baseado no funct

        # Está enviando o sinal padrao
        sinais_padrao = {
            'RegWrite': NAO, 
            'RegDst': REG_DST_RT, 
            'ALUSrc': ALU_SRC_REG,
            'ALUOp': ALU_OP_ADD, 
            'MemRead': NAO,  
            'MemWrite': NAO, 
            'MemToReg': MEM_TO_REG_ALU, 
            'Branch': NAO, 
            'Jump': NAO,
            'ALUControl': 'ADD'
        }


        tipo = info_tipo['type']
        subtipo = info_tipo.get('subtype', '')

        
        mapeamento_sinais = {
            # === R-TYPE ===
            'R': {
                **sinais_padrao,
                'RegWrite': SIM, 'RegDst': REG_DST_RD, 'ALUOp': ALU_OP_FUNCT,
                'ALUControl': self._mapear_funct_para_alu(subtipo)
            },
            
            # === I-TYPE ===
            'I': {
                **sinais_padrao,
                'RegWrite': SIM, 'ALUSrc': ALU_SRC_IMM,
                'ALUControl': self._mapear_opcode_para_alu(subtipo)
            },
            
            # === LOAD ===
            'lw': {
                **sinais_padrao,
                'RegWrite': SIM, 'ALUSrc': ALU_SRC_IMM, 'MemRead': SIM,
                'MemToReg': MEM_TO_REG_MEM, 'ALUControl': 'ADD'
            },
            
            # === STORE ===  
            'sw': {
                **sinais_padrao,
                'ALUSrc': ALU_SRC_IMM, 'MemWrite': SIM, 'MemRead': NAO, 'ALUControl': 'ADD'
            },
            
            # === BRANCH ===
            'branch': {
                **sinais_padrao,
                'ALUOp': ALU_OP_SUB, 'Branch': SIM, 'ALUControl': 'SUB'
            },
            
            # === JUMP ===
            'jump': {
                **sinais_padrao,
                'Jump': SIM, 'ALUControl': 'JUMP'
            },
            
            # === JAL ===
            'jal': {
                **sinais_padrao, 
                'RegWrite': SIM, 'Jump': SIM, 'ALUControl': 'JAL'
            }
        }
        

        # Retorna os sinais de controle
        # Inverti a ordem aqui pra priorizar o subtipo (lw/sw) antes do tipo (I)
        if subtipo in mapeamento_sinais:
            return mapeamento_sinais[subtipo]
        
        elif tipo in mapeamento_sinais:
            return mapeamento_sinais[tipo]
        
        else:
            return sinais_padrao




    def ID_stage(self):
        """
            Decodifica a instrução e prepara para execução.
        """

        # Controle de execução do ID_stage
        if not self.IF_ID['valid']:
            self.ID_EX['valid'] = False
            return

        
        instrucao = self.IF_ID['instruction']


        # Extração dos campos da instrução

        # Lógica do bitwise
        opcode = (instrucao >> 26) & 0x3F
        rs = (instrucao >> 21) & 0x1F
        rt = (instrucao >> 16) & 0x1F
        rd = (instrucao >> 11) & 0x1F
        shamt = (instrucao >> 6) & 0x1F
        funct = instrucao & 0x3F


        # Pega os 16 bits inferiores
        immediate = instrucao & 0xFFFF
        address = instrucao & 0x3FFFFFF  # Para jumps


        # Extensão de sinal
        immediate_signed = immediate
        if immediate & 0x8000:
            immediate_signed -= 0x10000

            
        # Detecção do tipo (segundo a abordagem do Lucas)
        info_tipo = self._detectar_tipo_instrucao(opcode, funct)


        # Verificar se tem conflito (hazard) antes de gerar sinais
        if self._verificar_conflito_memoria(rs, rt):
            # print("ID: Detectado conflito de Load-Use! Inserindo bolha...")
            self.stall_IF = True # Segura o IF
            self.ID_EX['valid'] = False # Manda nada pro EX
            return

        self.stall_IF = False # Libera se não tiver BO


        # Sinais de controle baseados no tipo (abordagem do Lucas)
        sinais_controle = self._gerar_sinais_controle(info_tipo)


        # Preenchimento da estrutura de dados.
        self.ID_EX.update({
            'opcode': opcode, 'rs': rs, 'rt': rt, 'rd': rd,
            'shamt': shamt, 'funct': funct,
            'immediate': immediate, 'immediate_signed': immediate_signed,
            'address': address,
            
            # Informação semântica
            'tipo': info_tipo['type'],
            'subtipo': info_tipo.get('subtype', 'unknown'),
            'descricao': info_tipo.get('descricao', ''),
            
            # Dados e controle
            'dado1': self.registradores[rs],
            'dado2': self.registradores[rt],
            'PC_mais_4': self.IF_ID['PC_mais_4'],
            'controle': sinais_controle,
            'PC_origem': self.IF_ID['PC'],
            'valid': True
        })




    def _shift_right_arithmetic(self, value, shamt):
        """ 
            Função auxiliar do EX_stage.
            Imeplementa lógica do SRA

        """

        shamt = shamt & 0x1F
        if value & 0x80000000:  # Negativo
            mask = (0xFFFFFFFF << (32 - shamt)) & 0xFFFFFFFF
            return (value >> shamt) | mask
        else:
            return value >> shamt


    def _executar_operacao_alu(self, alu_control, op1, op2, shamt=0):
        """
            Função auxiliar do EX_stage
            implementa a execução da ULA
        """

        # Força comportamento de 32 bits. 
        # A soma dos dois da overflow.
        op1 = op1 & 0xFFFFFFFF
        op2 = op2 & 0xFFFFFFFF

        operations = {
            # Operações básicas
            'ADD': lambda a, b: (a + b) & 0xFFFFFFFF,
            'SUB': lambda a, b: (a - b) & 0xFFFFFFFF,
            'AND': lambda a, b: a & b,
            'OR':  lambda a, b: a | b,
            'SLT': lambda a, b: 1 if (a & 0xFFFFFFFF) < (b & 0xFFFFFFFF) else 0,

            # Shifts 
            'SLL': lambda a, b: (a << (shamt & 0x1F)) & 0xFFFFFFFF,
            'SRL': lambda a, b: (a >> (shamt & 0x1F)) & 0xFFFFFFFF,
            'SRA': lambda a, b: self._shift_right_arithmetic(a, shamt),
        }    

        return operations.get(alu_control, lambda a, b: 0)(op1, op2)



    def _aplicar_jump(self, address, subtipo):
        """ 
            Função auxiliar da EX_stage para tratamento de branches
        """

        target = address << 2
        
        # Mantém os 4 bits superiores do PC atual (ID stage PC)
        pc_top = self.ID_EX['PC_mais_4'] & 0xF0000000
        
        if subtipo == 'j':
            self.PC = pc_top | target
        
        elif subtipo == 'jal':
            self.PC = pc_top | target

        self.IF_ID['valid'] = False
        self.ID_EX['valid'] = False
        self.rodando = True # Garante que a CPU nao morra no meio do pulo




    def _aplicar_branch(self, target):
        """
            Função auxiliar do EX_stage
            Aplica branch mudando o PC
        """
        
        self.PC = target
        self.IF_ID['valid'] = False
        self.ID_EX['valid'] = False
        self.rodando = True # Mantem rodando



    def EX_stage(self):
        """
            Executa operações ALU e calcula branches
        """

        # Atenção aqui em!!!!
    
        # Controle de execução.
        if not self.ID_EX['valid']:
            self.EX_MEM['valid'] = False
            return


        # Preparação dos dados
        # Shamt não está sendo usado (ID_EX)??

        opcode = self.ID_EX['opcode']
        rs = self.ID_EX['rs']
        rt = self.ID_EX['rt']
        rd = self.ID_EX['rd']
        funct = self.ID_EX['funct']
        immediate_signed = self.ID_EX['immediate_signed']
        dado1 = self.ID_EX['dado1']
        dado2 = self.ID_EX['dado2']
        controle = self.ID_EX['controle']
        tipo = self.ID_EX['tipo']
        subtipo = self.ID_EX['subtipo']
        PC_mais_4 = self.ID_EX['PC_mais_4']
        shamt = self.ID_EX['shamt']


        # Tratamento de adiantamento (Forwarding). Se o dado ta logo ali na frente, pega ele.
        operando1 = dado1
        operando2 = dado2
        val_store = dado2 

        # Forwarding pro Operando 1 (RS)
        if self.EX_MEM['valid'] and self.EX_MEM['RegWrite'] and self.EX_MEM['write_reg'] == rs and rs != 0:
             operando1 = self.EX_MEM['ALU_result']
        elif self.MEM_WB['valid'] and self.MEM_WB['RegWrite'] and self.MEM_WB['write_reg'] == rs and rs != 0:
             operando1 = self.MEM_WB['write_data']

        # Forwarding pro Operando 2 (RT)
        if self.EX_MEM['valid'] and self.EX_MEM['RegWrite'] and self.EX_MEM['write_reg'] == rt and rt != 0:
             temp_val = self.EX_MEM['ALU_result']
             operando2 = temp_val
             val_store = temp_val # Se for SW, o dado a ser salvo tbm precisa ser atualizado
        elif self.MEM_WB['valid'] and self.MEM_WB['RegWrite'] and self.MEM_WB['write_reg'] == rt and rt != 0:
             temp_val = self.MEM_WB['write_data']
             operando2 = temp_val
             val_store = temp_val


        # Verificar se usa imediate ou se vem do registrador
        if controle['ALUSrc'] == 1: 
            operando2 = immediate_signed # uso de sinal para as operações.
        

        # Execução da ULA.
        alu_result = self._executar_operacao_alu(
            controle['ALUControl'], 
            operando1,            
            operando2,
            shamt
        )


        # Controle de instrução: R usa rd e I usa rt
        write_reg = self.ID_EX['rd'] if controle['RegDst'] == 1 else self.ID_EX['rt']



        # Calculo de branches

        branch_target = 0
        branch_taken = False
        if controle['Branch']:
            branch_target = PC_mais_4 + (immediate_signed << 2)
            if alu_result == 0: # BEQ
                branch_taken = True
                self.rodando = True # Nao deixa parar no loop


        # Preenche EX_MEM
        self.EX_MEM.update({
            'ALU_result': alu_result,
            'write_data': val_store,
            'write_reg': write_reg,


            # Propagação dos sinais de controle. 
            'MemRead': controle.get('MemRead', False),
            'MemWrite': controle.get('MemWrite', False),
            'RegWrite': controle.get('RegWrite', False),
            'MemToReg': controle.get('MemToReg', False),


            # Controle de branches
            'Branch': controle.get('Branch', False),
            'branch_taken': branch_taken,
            'branch_target': branch_target if controle['Branch'] else 0,

            'valid': True
        })


        # Tratamento para branches e jumps

        if branch_taken:
            self._aplicar_branch(branch_target)
        elif controle.get('Jump', False):
            self._aplicar_jump(self.ID_EX['address'], subtipo)



    def MEM_stage(self):
        """
            Acessa memória de dados para loads/stores
        """


        # Controle de execução
        if not self.EX_MEM['valid']:
            self.MEM_WB['valid'] = False
            return

        # Dados da EX_MEM
        alu_result = self.EX_MEM['ALU_result']
        write_data = self.EX_MEM['write_data']
        write_reg = self.EX_MEM['write_reg']
        mem_read = self.EX_MEM['MemRead']
        mem_write = self.EX_MEM['MemWrite']
        reg_write = self.EX_MEM['RegWrite']
        mem_to_reg = self.EX_MEM['MemToReg'] # Para debug



        # Inicialização do write back
        write_back_data = alu_result


        # Operações de memória. 


        # load (lw): Leitura da memória.
        if mem_read:
            try:
                endereco = alu_result
                if hasattr(self, 'cache'):
                    write_back_data = self.cache.ler_palavra(endereco)
                else:
                    # Não tem na cache vai na memória principal. (simpres igual genro na casa do sogro)
                    write_back_data = self.cache.ram.ler_palavra(endereco)


            except Exception as e:
                # print(f"MEM: ERRO ao ler memória {hex(alu_result)}: {e}")
                self.rodando = False
                return

        # store (sw): Escreve na memória.
        elif mem_write:
            try:
                endereco = alu_result
                if hasattr(self, 'cache'):
                    self.cache.escrever_palavra(endereco, write_data)
                else:
                    self.cache.ram.escrever_palavra(endereco, write_data)

            except Exception as e:
                # print(f"MEM: ERRO ao escrever memória {hex(alu_result)}: {e}")
                self.rodando = False
                return
        #else:
            #print(" DEBUG MEM_stage: nao usou mem_write e nem mem_write" )


        # Preenchimento do MEM_WEB
        self.MEM_WB.update({
            'write_data': write_back_data,
            'write_reg': write_reg,
            'RegWrite': reg_write,
            'MemToReg': mem_to_reg,  # Dado vem da ULA ou da memoria?
            'valid': True
        })



    def WB_stage(self):
        """
            Escreve resultado final nos registradores
        """


        # Controle de execução.
        if not self.MEM_WB['valid']:
            return


        # Dados da MEM_WB
        write_data = self.MEM_WB['write_data']
        write_reg = self.MEM_WB['write_reg']
        reg_write = self.MEM_WB['RegWrite']

        
        # Escrita no banco de registradores (vetor[0] * 32).
        if reg_write and write_reg != 0: # Garante que a escrita não é no zero
            self.registradores[write_reg] = write_data & 0xFFFFFFFF  # Garante 32 bits


        # Estatistica (quantidade de instruções e outras possibilidades.)
        if reg_write and write_reg != 0:
            self.instrucoes_executadas += 1


    def executar_ciclo(self):
        """ Executa um ciclo completo do pipeline  """

        self.ciclo += 1

        # Ordem reversa: WB → MEM → EX → ID → IF
        self.WB_stage()    # 5. Write Back
        self.MEM_stage()   # 4. Memory Access
        self.EX_stage()    # 3. Execute
        self.ID_stage()    # 2. Instruction Decode
        self.IF_stage()    # 1. Instruction Fetch
