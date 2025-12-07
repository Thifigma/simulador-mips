class Cache:
    def __init__(self, memoria_principal):
        
        # A Cache precisa acessar a RAM quando der Miss
        self.ram = memoria_principal

        #Configuração da Cache
        self.tamanho_bloco = 16 # Cada bloco tem 16 bytes (4 palavras)
        self.num_linhas = 8     # A cache tem 8 linhas (slots)

        # Estrutura da Cache (lista de dicionários)
        # Cada linha tem: 'valid' (bit de validade), 'tab' (etiqueta) e dados (o bloco de bytes)
        self.linhas = [{
                'valid': False,
                'tag': 0,
                'dados': [0] * self.tamanho_bloco
            } for _ in range(self.num_linhas)]


        # Estatisticas para mostrar no final
        self.hits = 0
        self.misses = 0


    def _parse_endereco(self, endereco):
        """ 
            Divide o endereço em Tag, Index e Offset 
            
            Offset: Posição dentro do bloco (bits menos significativos)
             Index: Qual linha da cache usar
               Tag: Identificador do bloco na memória
        """

        offset = endereco % self.tamanho_bloco
        index = (endereco // self.tamanho_bloco) % self.num_linhas
        tag = endereco // (self.tamanho_bloco * self.num_linhas)

        return tag, index, offset



    def ler_byte(self, endereco):
        "Le um byte (para acessos de dados)"

        tag, index, offset = self._parse_endereco(endereco)
        linha = self.linhas[index]

        # Verifica se é HIT (Válido E Tag bate)
        if linha['valid'] and linha['tag'] == tag:
            self.hits += 1
            # print(f"CACHE: HIT no endereço {endereco}") # Comentei para não poluir muito
            return linha['dados'][offset]

        # Se for MISS
        else:
            self.misses += 1

            # print(f"CACHE: MISS @ {hex(endereco)}")


            # Trazendo o bloco da RAM para a Cache
            # Calcula onde começa o bloco na RAM (alinha o endereço)
            endereco_base = endereco - offset

            # Copia byte a byte da RAM para o array 'dados' da linha
            # Precisamos usar self.memoria.ler_byte, mas cuidado para não cair em loop infinito
            # Acessamos direto o array da RAM se possível, ou usamos o método ler da RAM
            for i in range(self.tamanho_bloco):
                linha['dados'][i] = self.ram.ler_byte(endereco_base + i)
           
            linha['tag'] = tag
            linha['valid'] = True
            return linha['dados'][offset]

    def escrever_byte(self, endereco, valor):
        """ Política Write-Through: Escreve na Cache E na RAM imediatamente """
        tag, index, offset = self._parse_endereco(endereco)
        linha = self.linhas[index]

        # 1. Escreve na RAM (Sempre, pois é Write-Through)
        self.ram.escrever_byte(endereco, valor)

        # 2. Se o bloco estiver na cache, atualizamos ele também
        if linha['valid'] and linha['tag'] == tag:
            linha['dados'][offset] = valor


    def ler_palavra(self, endereco):
        """
            Lê palavra de 32 bits - LITTLE-ENDIAN (MIPS)
        """
        
        if endereco % 4 != 0:
            raise Exception(f"Endereço não alinhado: {hex(endereco)}")

        palavra = 0
        for i in range(4):
            byte = self.ler_byte(endereco + i)
            palavra |= (byte << (8 * i))  # Little-endian: byte[i] na posição 8*i


        return palavra


    def escrever_palavra(self, endereco, valor):
        """
            Escreve palavra de 32 bits - LITTLE-ENDIAN (MIPS)
        """

        if endereco % 4 != 0:
            raise Exception(f"Endereço não alinhado: {hex(endereco)}")

        for i in range(4):
            byte = (valor >> (8 * i)) & 0xFF  # Little-endian: pega byte[i]
            self.escrever_byte(endereco + i, byte)


    def imprimir_estatisticas(self):

        total = self.hits + self.misses

        if total > 0:
            taxa_hit = (self.hits / total) * 100
            print(f"\n Estatísticas da Cache: \n")
            print(f"   Hits: {self.hits} | Misses: {self.misses}")
            print(f"   Taxa de Hit: {taxa_hit:.1f}%")

