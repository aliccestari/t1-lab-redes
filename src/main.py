import sys
from ring_node import RingNode

def main():
    if len(sys.argv) != 3:
        print("Uso: python3 main.py <arquivo_configuracao> <porta_escuta>")
        sys.exit(1)
    config_file = sys.argv[1]
    listen_port = int(sys.argv[2])
    node = RingNode(config_file, listen_port)
    node.start()

if __name__ == "__main__":
    main() 