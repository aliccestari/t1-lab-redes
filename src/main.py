import sys
import threading
from device import Device

def print_help():
    print("Comandos disponíveis:")
    print("  devices - Lista os dispositivos ativos na rede")
    print("  talk <nome> <mensagem> - Envia uma mensagem para um dispositivo")
    print("  sendfile <nome> <arquivo> - Envia um arquivo para um dispositivo")
    print("  savefile <id> <nome_destino> - Salva um arquivo recebido pelo id da transferência")
    print("  help - Mostra esta ajuda")
    print("  exit - Encerra o programa")

def main():
    if len(sys.argv) < 2 or len(sys.argv) > 3:
        print("Uso: python main.py <nome_do_dispositivo> [porta]")
        sys.exit(1)
        
    device_name = sys.argv[1]
    port = int(sys.argv[2]) if len(sys.argv) == 3 else 5000
    
    print(f"Iniciando dispositivo {device_name} na porta {port}...")
    device = Device(device_name, port)
    device.start()
    
    print("Digite 'help' para ver os comandos disponíveis.")
    
    try:
        while True:
            command = input("> ").strip()
            
            if command == "help":
                print_help()
                
            elif command == "devices":
                active_devices = device.list_devices()
                if not active_devices:
                    print("Nenhum dispositivo ativo encontrado.")
                else:
                    print("\nDispositivos ativos:")
                    for dev in active_devices:
                        print(f"  - {dev.name} ({dev.ip}:{dev.port})")
                    print()
                    
            elif command.startswith("talk "):
                parts = command.split(" ", 2)
                if len(parts) != 3:
                    print("Uso: talk <nome> <mensagem>")
                    continue
                    
                target_name = parts[1]
                message = parts[2]
                if device.send_message(target_name, message):
                    print(f"Mensagem enviada para {target_name}")
                else:
                    print(f"Falha ao enviar mensagem para {target_name}")
                
            elif command.startswith("sendfile "):
                parts = command.split(" ", 2)
                if len(parts) != 3:
                    print("Uso: sendfile <nome> <arquivo>")
                    continue
                target_name = parts[1]
                filename = parts[2]
                if device.send_file(target_name, filename):
                    print(f"Solicitação de envio de arquivo enviada para {target_name}")
                else:
                    print(f"Falha ao enviar solicitação de arquivo para {target_name}")
                
            elif command.startswith("savefile "):
                parts = command.split(" ", 2)
                if len(parts) != 3:
                    print("Uso: savefile <id> <nome_destino>")
                    continue
                msg_id = parts[1]
                dest_filename = parts[2]
                device.save_received_file(msg_id, dest_filename)
                
            elif command == "exit":
                break
                
            else:
                print("Comando desconhecido. Digite 'help' para ver os comandos disponíveis.")
                
    except KeyboardInterrupt:
        print("\nEncerrando...")
    finally:
        device.stop()

if __name__ == "__main__":
    main() 