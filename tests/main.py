import sys
from tests.device import Device

def print_menu():
    print("\nEscolha uma opção:")
    print("1. devices")
    print("2. talk <nome> <mensagem> ")
    print("3. sendfile <nome> <nome-arquivo>")
    print("4. sair")

def main():
    if len(sys.argv) < 2 or len(sys.argv) > 3:
        print("Uso: python main.py <nome_do_dispositivo> [porta]")
        sys.exit(1)
    device_name = sys.argv[1]
    port = int(sys.argv[2]) if len(sys.argv) == 3 else 5000
    print(f"Iniciando dispositivo {device_name} na porta {port}...")
    device = Device(device_name, port)
    device.start()
    try:
        while True:
            print_menu()
            command = input("> ").strip()
            if command == "1" or command == "devices":
                active_devices = device.list_devices()
                if not active_devices:
                    print("Nenhum dispositivo ativo encontrado.")
                else:
                    print("\nDispositivos ativos:")
                    for dev in active_devices:
                        print(f"  - {dev.name} ({dev.ip}:{dev.port})")
            elif command.startswith("2") or command.startswith("talk "):
                if command.startswith("2"):
                    parts = input("Digite o nome do destinatário e a mensagem (ex: dispositivo2 Olá): ").strip().split(" ", 1)
                else:
                    parts = command.split(" ", 2)[1:]
                if len(parts) != 2:
                    print("Uso: talk <nome> <mensagem>")
                    continue
                target_name, message = parts
                if device.send_message(target_name, message):
                    print(f"Mensagem enviada para {target_name}")
                else:
                    print(f"Falha ao enviar mensagem para {target_name}")
            elif command.startswith("3") or command.startswith("sendfile "):
                if command.startswith("3"):
                    parts = input("Digite o nome do destinatário e o nome do arquivo (ex: dispositivo2 teste.txt): ").strip().split(" ", 1)
                else:
                    parts = command.split(" ", 2)[1:]
                if len(parts) != 2:
                    print("Uso: sendfile <nome> <nome-arquivo>")
                    continue
                target_name, filename = parts
                if device.send_file(target_name, filename):
                    print(f"Solicitação de envio de arquivo enviada para {target_name}")
                else:
                    print(f"Falha ao enviar solicitação de arquivo para {target_name}")
            elif command == "4" or command == "sair":
                print("Saindo...")
                break
            else:
                print("Opção inválida. Tente novamente.")
    except KeyboardInterrupt:
        print("\nEncerrando...")
    finally:
        device.stop()

if __name__ == "__main__":
    main() 