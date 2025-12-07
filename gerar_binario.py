import struct

print("Gerando binário: Soma de Vetores (Versão Final com NOPs)...")

regs = {
    '$zero':0, '$at':1, '$v0':2, '$v1':3, '$a0':4, '$a1':5, '$a2':6, '$a3':7,
    '$t0':8,  '$t1':9,  '$t2':10, '$t3':11, '$t4':12, '$t5':13, '$t6':14, '$t7':15,
    '$s0':16, '$s1':17, '$s2':18, '$s3':19, '$s4':20, '$s5':21, '$s6':22, '$s7':23,
    '$t8':24, '$t9':25, '$k0':26, '$k1':27, '$gp':28, '$sp':29, '$fp':30, '$ra':31
}

def R(opcode, funct, rd, rs, rt, shamt=0):
    return (opcode << 26) | (regs[rs] << 21) | (regs[rt] << 16) | (regs[rd] << 11) | (shamt << 6) | funct

def I(opcode, rt, rs, imm):
    if imm < 0: imm = (1 << 16) + imm
    return (opcode << 26) | (regs[rs] << 21) | (regs[rt] << 16) | (imm & 0xFFFF)

def J_TYPE(opcode, address):
    return (opcode << 26) | (address & 0x3FFFFFF)

def ASM_ADD(rd, rs, rt): return R(0, 0x20, rd, rs, rt)
def ASM_ADDI(rt, rs, imm): return I(0x08, rt, rs, imm)
def ASM_LW(rt, offset, rs): return I(0x23, rt, rs, offset)
def ASM_SW(rt, offset, rs): return I(0x2B, rt, rs, offset)
def ASM_BEQ(rs, rt, offset): return I(0x04, rt, rs, offset)
def ASM_J(target_instr_index): return J_TYPE(0x02, target_instr_index)
def ASM_NOP(): return ASM_ADD('$zero', '$zero', '$zero') 

instrucoes = [
    # A. SETUP
    ASM_ADDI('$s0', '$zero', 200),
    ASM_ADDI('$s1', '$zero', 300),
    ASM_ADDI('$s2', '$zero', 400),

    # B. DADOS V1
    ASM_ADDI('$t0', '$zero', 0), ASM_SW('$t0', 0, '$s0'),
    ASM_ADDI('$t0', '$zero', 2), ASM_SW('$t0', 4, '$s0'),
    ASM_ADDI('$t0', '$zero', 4), ASM_SW('$t0', 8, '$s0'),
    ASM_ADDI('$t0', '$zero', 6), ASM_SW('$t0', 12, '$s0'),
    ASM_ADDI('$t0', '$zero', 8), ASM_SW('$t0', 16, '$s0'),
    ASM_ADDI('$t0', '$zero', 10), ASM_SW('$t0', 20, '$s0'),

    # C. DADOS V2
    ASM_ADDI('$t0', '$zero', 1), ASM_SW('$t0', 0, '$s1'),
    ASM_ADDI('$t0', '$zero', 3), ASM_SW('$t0', 4, '$s1'),
    ASM_ADDI('$t0', '$zero', 5), ASM_SW('$t0', 8, '$s1'),
    ASM_ADDI('$t0', '$zero', 7), ASM_SW('$t0', 12, '$s1'),
    ASM_ADDI('$t0', '$zero', 9), ASM_SW('$t0', 16, '$s1'),
    ASM_ADDI('$t0', '$zero', 11), ASM_SW('$t0', 20, '$s1'),

    # D. LOOP
    ASM_ADDI('$t1', '$zero', 0),    # i = 0
    ASM_ADDI('$t2', '$zero', 24),   # Limit = 24

    # --- LOOP START (Index 29) ---
    ASM_ADD('$t6', '$s0', '$t1'),   # Calcula endereço V1
    ASM_LW('$t3', 0, '$t6'),        # Carrega V1[i]

    ASM_ADD('$t6', '$s1', '$t1'),   # Calcula endereço V2
    ASM_LW('$t4', 0, '$t6'),        # Carrega V2[i]

    # --- NOPS CRÍTICOS ---
    ASM_NOP(),
    ASM_NOP(),
    ASM_NOP(),

    ASM_ADD('$t5', '$t3', '$t4'),   # Soma: V1[i] + V2[i]
    
    # --- NOPS PARA O STORE ---
    ASM_NOP(),
    ASM_NOP(),

    ASM_ADD('$t6', '$s2', '$t1'),   # Calcula endereço V3
    ASM_SW('$t5', 0, '$t6'),        # Guarda em V3

    ASM_ADDI('$t1', '$t1', 4),      # Incrementa i

    # --- NOPS PARA O BRANCH ---
    ASM_NOP(),
    ASM_NOP(),
    ASM_NOP(),

    ASM_BEQ('$t1', '$t2', 1),       # Se i == 24, sai
    ASM_J(29),                      # Volta pro início

    ASM_NOP(),                      # Pouso do Branch (Delay Slot)
    
    0xFFFFFFFF                      # HALT (Para o simulador)
]

with open("teste.bin", "wb") as f:
    for instr in instrucoes:
        f.write(struct.pack('>I', instr))

print(f"Sucesso! Binário gerado com {len(instrucoes)} instruções.")