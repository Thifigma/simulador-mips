from cpu import Processador
from cache import Cache
from memoria import Memoria 

# Mapa de nomes de registradores para facilitar o debug visual
nomes_registradores = {
    0: '$zero', 1: '$at', 2: '$v0', 3: '$v1',
    4: '$a0', 5: '$a1', 6: '$a2', 7: '$a3',
    8: '$t0', 9: '$t1', 10: '$t2', 11: '$t3', 12: '$t4', 13: '$t5', 14: '$t6', 15: '$t7',
    16: '$s0', 17: '$s1', 18: '$s2', 19: '$s3', 20: '$s4', 21: '$s5', 22: '$s6', 23: '$s7',
    24: '$t8', 25: '$t9', 26: '$k0', 27: '$k1', 28: '$gp', 29: '$sp', 30: '$fp', 31: '$ra'
}

def carregar_programa(memoria, arquivo="programa.bin", endereco_inicio=0):
    try:
        with open(arquivo, "rb") as f:
            dados = f.read()

        for i in range(0, len(dados), 4):
            palavra_bytes = dados[i:i+4]
            if len(palavra_bytes) == 4:
                palavra = int.from_bytes(palavra_bytes, byteorder='big')
                memoria.escrever_palavra(endereco_inicio + i, palavra)

        print(f"Programa carregado: {len(dados)} bytes em {hex(endereco_inicio)}")
        return len(dados)        

    except FileNotFoundError:
        print(f"Arquivo {arquivo} não encontrado")
        return 0
    except Exception as e:
        print(f"Erro ao carregar binário: {e}")
        return 0

def main():
    
    memoria_principal = Memoria()
    cache = Cache(memoria_principal)
    cpu = Processador(cache)

    carregar_programa(
        memoria_principal,
        arquivo="teste.bin",
        endereco_inicio=memoria_principal.text_inicio 
    )

    cpu.PC = memoria_principal.text_inicio
    max_ciclos = 1000
    ciclos_executados = 0

    try:
        print("\n" + "="*60)
        print(" INICIANDO A SIMULAÇÃO DETALHADA DO PIPELINE ")
        print("="*60 + "\n")

        while cpu.rodando and ciclos_executados < max_ciclos:
            
            # Cabeçalho do Ciclo
            print(f"--- CICLO {ciclos_executados:03d} " + "-"*45)
            
            cpu.executar_ciclo()
            ciclos_executados += 1

            # ---------------------------------------------------------
            # 1. WRITE BACK (WB)
            # ---------------------------------------------------------
            if cpu.MEM_WB['valid']:
                reg_num = cpu.MEM_WB['write_reg']
                if cpu.MEM_WB['RegWrite'] and reg_num != 0:
                    reg_nome = nomes_registradores.get(reg_num, f"${reg_num}")
                    val = cpu.MEM_WB['write_data']
                    print(f"  [WB]  ESCRITA : Reg {reg_nome} recebe {hex(val)} (Dec: {val})")
                else:
                    print(f"  [WB]  Nenhuma escrita em registrador.")

            # ---------------------------------------------------------
            # 2. MEMORY (MEM)
            # ---------------------------------------------------------
            if cpu.EX_MEM['valid']:
                if cpu.EX_MEM['MemRead']:
                    addr = cpu.EX_MEM['ALU_result']
                    print(f"  [MEM] LEITURA : Lendo endereço {hex(addr)} (LW)")
                elif cpu.EX_MEM['MemWrite']:
                    addr = cpu.EX_MEM['ALU_result']
                    val = cpu.EX_MEM['write_data']
                    print(f"  [MEM] GRAVANDO: Valor {val} (Hex: {hex(val)}) no endereço {hex(addr)} (SW)")
                else:
                    print(f"  [MEM] Passagem: Apenas repassando dados (sem acesso à RAM)")

            # ---------------------------------------------------------
            # 3. EXECUTE (EX)
            # ---------------------------------------------------------
            if cpu.ID_EX['valid']:
                nome_instr = cpu.ID_EX.get('subtipo', cpu.ID_EX['tipo']).upper()
                res_alu = cpu.EX_MEM['ALU_result']
                
                msg_branch = ""
                if cpu.EX_MEM['Branch']:
                    status = "TOMADO" if cpu.EX_MEM['branch_taken'] else "NÃO TOMADO"
                    msg_branch = f"-> Branch {status}"

                print(f"  [EX]  EXECUÇÃO: {nome_instr} | Resultado ULA: {hex(res_alu)} {msg_branch}")

            # ---------------------------------------------------------
            # 4. DECODE (ID)
            # ---------------------------------------------------------
            if cpu.ID_EX['valid']:
                tipo = cpu.ID_EX.get('subtipo', 'instrução')
                print(f"  [ID]  DECODE  : Preparando instrução '{tipo.upper()}'")

            # ---------------------------------------------------------
            # 5. FETCH (IF)
            # ---------------------------------------------------------
            if cpu.IF_ID['valid']:
                pc_atual = cpu.IF_ID['PC']
                hex_instr = cpu.IF_ID['instruction']
                print(f"  [IF]  BUSCA   : PC {hex(pc_atual)} -> Instrução {hex(hex_instr)}")
            else:
                print(f"  [IF]  BUSCA   : (Stall ou Fim)")


            # Verifica parada
            if not cpu.rodando:
                print("\n" + "="*60)
                print(" CPU PAROU - FIM DO PROGRAMA ")
                print("="*60 + "\n")
                break
            
            # Espaço entre ciclos
            print("") 

    except KeyboardInterrupt:
        print("\n Execução interrompida pelo usuário!\n")
    except Exception as e:
        print(f"\n Deu algum erro bizarro: {e} \n")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()