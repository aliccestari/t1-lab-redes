# Protocolo de Comunicação Distribuída

Este projeto implementa um protocolo de comunicação customizado sobre UDP para descoberta e comunicação entre dispositivos em uma rede local.

## Funcionalidades

- Descoberta automática de dispositivos na rede
- Envio de mensagens entre dispositivos
- Transferência de arquivos com confiabilidade
- Interface de linha de comando interativa

## Requisitos

- Python 3.8 ou superior
- Dependências listadas em `requirements.txt`

## Instalação

1. Clone o repositório
2. Instale as dependências:
```bash
pip install -r requirements.txt
```

## Uso

Para iniciar um dispositivo:

```bash
python src/main.py <nome_do_dispositivo>
```

Comandos disponíveis:
- `devices` - Lista os dispositivos ativos na rede
- `talk <nome> <mensagem>` - Envia uma mensagem para um dispositivo
- `sendfile <nome> <arquivo>` - Envia um arquivo para um dispositivo
- `help` - Mostra a ajuda
- `exit` - Encerra o programa

## Protocolo

O protocolo implementa os seguintes tipos de mensagens:

- HEARTBEAT: Para descoberta de dispositivos
- TALK: Para comunicação entre dispositivos
- FILE: Para iniciar transferência de arquivos
- CHUNK: Para transferência de blocos de arquivos
- END: Para finalizar transferência de arquivos
- ACK: Para confirmação de recebimento
- NACK: Para indicar erro no processamento

## Estrutura do Projeto

- `src/device.py`: Implementação do protocolo e lógica do dispositivo
- `src/main.py`: Interface de linha de comando
- `tests/`: Testes do projeto 