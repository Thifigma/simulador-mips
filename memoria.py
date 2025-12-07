class Memoria:
    def __init__(self, tamanho=1024*1024):  # 1MB por padrão

        #self.dados = bytearray(tamanho)
        
        """ 
            Essa abordagem é mais fiel ao hardware, vale a pena discutir depois isso.
             Por agora deixei como vetor, como o Lucas sugeriu
        """
        
        self.dados = [0] * tamanho
        self.definir_secoes()

    def definir_secoes(self):
        """Define as seções de memória"""
        
        self.text_inicio = 0x0000
        self.text_fim = 0xFFFF

        self.dados_inicio = 0x10000
        self.dados_fim = 0x1FFFF

        self.pilha_inicio = 0x20000
        self.pilha_fim = 0x2FFFF

    # AQUI É BYTE A BYTE. É o que está sendo usado.

    def ler_byte(self, endereco):
        """ 
            Retorna o BYTE daquele endereço 
        """

        if 0 <= endereco < len(self.dados):
            return self.dados[endereco]
        else:
            raise Exception(f"Erro de Segmentação: Acesso inválido a {endereco}")


    def escrever_byte(self, endereco, valor):
        """ 
            Escreve um BYTE 
        """

        if 0 <= endereco < len(self.dados):
            self.dados[endereco] = valor & 0xFF # Garante que é só 8 bits


        # TRATAMENTO DE PALAVRAS (32 BITS) 4 BYTES


    def ler_palavra(self, endereco):
        """
            Lê 4 bytes como uma palavra de 32 bits
        """

        palavra = 0
        for i in range(4):
            byte = self.ler_byte(endereco + i)
            palavra |= (byte << (8 * i))  # Little-endian
        
        return palavra


    def escrever_palavra(self, endereco, valor):
        """ 
            Escreve uma palavra de 32 bits em 4 bytes
        """
        
        for i in range(4):
            byte = (valor >> (8 * i)) & 0xFF  # Little-endian
            self.escrever_byte(endereco + i, byte)


    def carregar_programa(self, instrucoes):
        """
            Responsável por carregar as instruções na memória.
        """
        ...

    def carregar_dados(self, dados):
        """
            Responsável por carregar os dados na seção dados da memória.
        """
        ...
