import socket
import threading
import time
import json
import uuid
import os
import base64
import hashlib
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime

@dataclass
class DeviceInfo:
    name: str
    ip: str
    port: int
    last_heartbeat: datetime

class Device:
    def __init__(self, name: str, port: int = 5000):
        self.name = name
        self.port = port
        
        # Socket para receber mensagens
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind(('', port))
        
        # Lista de dispositivos conhecidos
        self.known_devices: Dict[str, DeviceInfo] = {}
        
        # Dicionário para rastrear mensagens pendentes de ACK
        self.pending_acks: Dict[str, tuple] = {}
        
        # Threads
        self.receive_thread = threading.Thread(target=self._receive_loop)
        self.heartbeat_thread = threading.Thread(target=self._heartbeat_loop)
        self.ack_thread = threading.Thread(target=self._ack_loop)
        
        # Flags de controle
        self.running = True
        
        self.file_send_state = None  # (msg_id, filename, filesize, target, next_seq, pending_chunks)
        self.file_recv_state = {}    # msg_id: {filename, filesize, received_chunks, total_chunks, data_chunks}
        
    def start(self):
        """Inicia o dispositivo e suas threads"""
        self.receive_thread.start()
        self.heartbeat_thread.start()
        self.ack_thread.start()
        print(f"Dispositivo {self.name} iniciado na porta {self.port}")
        self._send_heartbeat()  # Envia HEARTBEAT inicial
        
    def stop(self):
        """Para o dispositivo e suas threads"""
        self.running = False
        self.socket.close()
        self.receive_thread.join()
        self.heartbeat_thread.join()
        self.ack_thread.join()
        
    def _receive_loop(self):
        """Loop principal de recebimento de mensagens"""
        while self.running:
            try:
                data, addr = self.socket.recvfrom(1024)
                self._handle_message(data, addr)
            except Exception as e:
                if self.running:
                    print(f"Erro ao receber mensagem: {e}")
                    
    def _heartbeat_loop(self):
        """Loop de envio de mensagens HEARTBEAT"""
        while self.running:
            try:
                self._send_heartbeat()
            except Exception as e:
                print(f"Erro ao enviar HEARTBEAT: {e}")
            time.sleep(5)
            
    def _ack_loop(self):
        """Loop para verificar ACKs pendentes"""
        while self.running:
            current_time = time.time()
            # Verifica mensagens TALK/FILE pendentes
            for msg_id, (message, addr, timestamp) in list(self.pending_acks.items()):
                if current_time - timestamp > 2.0:
                    self.socket.sendto(message.encode(), addr)
                    self.pending_acks[msg_id] = (message, addr, time.time())
            # Verifica CHUNKs pendentes
            if self.file_send_state:
                for seq, (chunk_msg, addr, timestamp) in list(self.file_send_state['pending_chunks'].items()):
                    if current_time - timestamp > 2.0:
                        self.socket.sendto(chunk_msg.encode(), addr)
                        self.file_send_state['pending_chunks'][seq] = (chunk_msg, addr, time.time())
            time.sleep(0.1)
            
    def _send_heartbeat(self):
        """Envia mensagem HEARTBEAT para dispositivos conhecidos"""
        message = f"HEARTBEAT {self.name}"
        try:
            # Envia para todos os dispositivos conhecidos
            for device in self.known_devices.values():
                if device.port != self.port:  # Não envia para a própria porta
                    self.socket.sendto(message.encode(), ('127.0.0.1', device.port))
            
            # Envia para a porta padrão (5000) se não houver dispositivos conhecidos
            if not self.known_devices and self.port != 5000:
                self.socket.sendto(message.encode(), ('127.0.0.1', 5000))
                
        except Exception as e:
            print(f"Erro ao enviar HEARTBEAT: {e}")
            
    def send_message(self, target_name: str, message: str) -> bool:
        """Envia uma mensagem para um dispositivo específico"""
        if target_name not in self.known_devices:
            print(f"Dispositivo {target_name} não encontrado")
            return False
            
        target = self.known_devices[target_name]
        msg_id = str(uuid.uuid4())
        talk_message = f"TALK {msg_id} {message}"
        
        try:
            self.socket.sendto(talk_message.encode(), ('127.0.0.1', target.port))
            self.pending_acks[msg_id] = (talk_message, ('127.0.0.1', target.port), time.time())
            return True
        except Exception as e:
            print(f"Erro ao enviar mensagem: {e}")
            return False
        
    def send_file(self, target_name: str, filename: str) -> bool:
        """Inicia o envio de um arquivo para um dispositivo específico"""
        if target_name not in self.known_devices:
            print(f"Dispositivo {target_name} não encontrado")
            return False
        if not os.path.isfile(filename):
            print(f"Arquivo '{filename}' não encontrado")
            return False
        target = self.known_devices[target_name]
        msg_id = str(uuid.uuid4())
        filesize = os.path.getsize(filename)
        file_message = f"FILE {msg_id} {os.path.basename(filename)} {filesize}"
        try:
            self.socket.sendto(file_message.encode(), ('127.0.0.1', target.port))
            self.pending_acks[msg_id] = (file_message, ('127.0.0.1', target.port), time.time())
            self.file_send_state = {
                'msg_id': msg_id,
                'filename': filename,
                'filesize': filesize,
                'target': target,
                'next_seq': 0,
                'pending_chunks': {},
                'acknowledged': False
            }
            print(f"Solicitação de envio de arquivo enviada para {target_name}")
            return True
        except Exception as e:
            print(f"Erro ao enviar FILE: {e}")
            return False
        
    def _handle_message(self, data: bytes, addr: tuple):
        """Processa mensagens recebidas"""
        try:
            message = data.decode()
            parts = message.split()
            
            if parts[0] == "HEARTBEAT":
                self._handle_heartbeat(parts[1], addr)
            elif parts[0] == "TALK":
                self._handle_talk(parts[1], parts[2:], addr)
            elif parts[0] == "ACK":
                self._handle_ack(parts[1])
            elif parts[0] == "FILE":
                self._handle_file(parts[1], parts[2:], addr)
            elif parts[0] == "CHUNK":
                self._handle_chunk(parts[1], parts[2:], addr)
            elif parts[0] == "END":
                self._handle_end(parts[1], parts[2:], addr)
            elif parts[0] == "NACK":
                self._handle_nack(parts[1], parts[2:], addr)
                
        except Exception as e:
            print(f"Erro ao processar mensagem: {e}")
            
    def _handle_heartbeat(self, device_name: str, addr: tuple):
        """Atualiza lista de dispositivos com novo HEARTBEAT"""
        if device_name != self.name:  # Ignora próprios HEARTBEATs
            device_info = DeviceInfo(
                name=device_name,
                ip=addr[0],
                port=addr[1],
                last_heartbeat=datetime.now()
            )
            # Atualiza ou adiciona dispositivo
            if device_name not in self.known_devices:
                print(f"Novo dispositivo {device_name} detectado em {addr[0]}:{addr[1]}")
            self.known_devices[device_name] = device_info
            
    def _handle_talk(self, msg_id: str, message_parts: List[str], addr: tuple):
        """Processa mensagem TALK recebida"""
        message = ' '.join(message_parts)
        print(f"\nMensagem recebida: {message}\n")
        
        # Envia ACK
        ack_message = f"ACK {msg_id}"
        try:
            self.socket.sendto(ack_message.encode(), addr)
        except Exception as e:
            print(f"Erro ao enviar ACK: {e}")
            
    def _handle_ack(self, msg_id: str):
        """Processa ACK recebido"""
        if msg_id in self.pending_acks:
            del self.pending_acks[msg_id]
            print(f"Mensagem {msg_id} confirmada")
            # Se for ACK do FILE, começa a enviar os CHUNKs
            if self.file_send_state and self.file_send_state['msg_id'] == msg_id and not self.file_send_state['acknowledged']:
                self.file_send_state['acknowledged'] = True
                threading.Thread(target=self._send_file_chunks).start()
            # Se for ACK do END, finaliza
            if self.file_send_state and msg_id == self.file_send_state['msg_id'] + '_END':
                print("Transferência de arquivo finalizada com sucesso!")
                self.file_send_state = None
        
    def _handle_file(self, msg_id: str, file_parts: list, addr: tuple):
        """Processa mensagem FILE recebida"""
        filename = file_parts[0]
        filesize = file_parts[1]
        print(f"\nSolicitação de recebimento de arquivo: {filename} ({filesize} bytes) de {addr[0]}:{addr[1]}")
        # Envia ACK
        ack_message = f"ACK {msg_id}"
        try:
            self.socket.sendto(ack_message.encode(), addr)
        except Exception as e:
            print(f"Erro ao enviar ACK de FILE: {e}")
        
    def _handle_chunk(self, msg_id: str, chunk_parts: list, addr: tuple):
        seq = int(chunk_parts[0])
        b64data = chunk_parts[1]
        data = base64.b64decode(b64data)
        # Inicializa estado de recebimento se necessário
        if msg_id not in self.file_recv_state:
            self.file_recv_state[msg_id] = {
                'received_chunks': {},
                'data_chunks': {},
            }
        state = self.file_recv_state[msg_id]
        if seq not in state['received_chunks']:
            state['received_chunks'][seq] = True
            state['data_chunks'][seq] = data
            print(f"Recebido bloco {seq} do arquivo (id {msg_id})")
        # Envia ACK do bloco
        ack_message = f"ACK {msg_id}"
        try:
            self.socket.sendto(ack_message.encode(), addr)
        except Exception as e:
            print(f"Erro ao enviar ACK de CHUNK: {e}")
        # (No futuro: salvar arquivo completo e verificar END)
        
    def list_devices(self):
        """Lista dispositivos ativos"""
        current_time = datetime.now()
        active_devices = []
        inactive_devices = []
        
        for device in self.known_devices.values():
            time_diff = (current_time - device.last_heartbeat).total_seconds()
            if time_diff <= 10:  # Dispositivo ativo nos últimos 10 segundos
                active_devices.append(device)
            else:
                inactive_devices.append(device.name)
                
        # Remove dispositivos inativos
        for device_name in inactive_devices:
            del self.known_devices[device_name]
            print(f"Dispositivo {device_name} removido por inatividade")
                
        return active_devices 

    def _send_file_chunks(self):
        state = self.file_send_state
        if not state:
            return
        filename = state['filename']
        msg_id = state['msg_id']
        target = state['target']
        chunk_size = 1024
        seq = 0
        try:
            with open(filename, 'rb') as f:
                while True:
                    data = f.read(chunk_size)
                    if not data:
                        break
                    b64data = base64.b64encode(data).decode()
                    chunk_msg = f"CHUNK {msg_id} {seq} {b64data}"
                    self.socket.sendto(chunk_msg.encode(), ('127.0.0.1', target.port))
                    state['pending_chunks'][seq] = (chunk_msg, ('127.0.0.1', target.port), time.time())
                    acked = False
                    for _ in range(20):
                        if seq not in state['pending_chunks']:
                            acked = True
                            break
                        time.sleep(0.1)
                    if not acked:
                        print(f"Timeout esperando ACK do bloco {seq}, retransmitindo...")
                        self.socket.sendto(chunk_msg.encode(), ('127.0.0.1', target.port))
                        state['pending_chunks'][seq] = (chunk_msg, ('127.0.0.1', target.port), time.time())
                    seq += 1
            print(f"Arquivo {filename} enviado com sucesso!")
            # Calcula hash e envia END
            file_hash = self._calculate_file_hash(filename)
            end_msg = f"END {msg_id} {file_hash}"
            self.socket.sendto(end_msg.encode(), ('127.0.0.1', target.port))
            self.pending_acks[msg_id + '_END'] = (end_msg, ('127.0.0.1', target.port), time.time())
        except Exception as e:
            print(f"Erro ao enviar arquivo: {e}")

    def _calculate_file_hash(self, filename: str) -> str:
        sha256 = hashlib.sha256()
        with open(filename, 'rb') as f:
            while True:
                data = f.read(4096)
                if not data:
                    break
                sha256.update(data)
        return sha256.hexdigest()

    def _handle_end(self, msg_id: str, end_parts: list, addr: tuple):
        """Processa mensagem END recebida, verifica integridade e responde com ACK ou NACK"""
        received_hash = end_parts[0]
        if msg_id not in self.file_recv_state:
            print(f"Arquivo com id {msg_id} não encontrado para verificação de hash.")
            return
        state = self.file_recv_state[msg_id]
        # Salva arquivo temporário para calcular hash
        temp_filename = f"temp_{msg_id}.bin"
        self.save_received_file(msg_id, temp_filename)
        local_hash = self._calculate_file_hash(temp_filename)
        if local_hash == received_hash:
            print(f"Arquivo recebido com sucesso e verificado! Hash: {local_hash}")
            ack_message = f"ACK {msg_id}_END"
            self.socket.sendto(ack_message.encode(), addr)
        else:
            print(f"Arquivo corrompido! Hash esperado: {received_hash}, hash calculado: {local_hash}")
            nack_message = f"NACK {msg_id}_END hash_invalido"
            self.socket.sendto(nack_message.encode(), addr)
        # Remove arquivo temporário
        try:
            os.remove(temp_filename)
        except Exception:
            pass

    def _handle_nack(self, msg_id: str, nack_parts: list, addr: tuple):
        print(f"Recebido NACK para {msg_id}: {' '.join(nack_parts)}")
        if self.file_send_state and msg_id == self.file_send_state['msg_id'] + '_END':
            print("Transferência de arquivo falhou por integridade!")
            self.file_send_state = None

    def save_received_file(self, msg_id: str, dest_filename: str) -> bool:
        """Salva o arquivo recebido em disco a partir dos blocos armazenados"""
        if msg_id not in self.file_recv_state:
            print(f"Arquivo com id {msg_id} não encontrado.")
            return False
        state = self.file_recv_state[msg_id]
        data_chunks = state['data_chunks']
        if not data_chunks:
            print(f"Nenhum bloco recebido para o arquivo {msg_id}.")
            return False
        # Salva os blocos em ordem de sequência
        try:
            with open(dest_filename, 'wb') as f:
                for seq in sorted(data_chunks.keys()):
                    f.write(data_chunks[seq])
            print(f"Arquivo salvo como {dest_filename}")
            return True
        except Exception as e:
            print(f"Erro ao salvar arquivo: {e}")
            return False 