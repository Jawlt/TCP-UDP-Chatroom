import socket
import threading

# ServerTCP Class
class ServerTCP:
    def __init__(self, server_port):
        self.server_port = server_port
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind(('localhost', server_port))
        self.server_socket.listen(5)
        self.clients = {}
        self.run_event = threading.Event()
        self.handle_event = threading.Event() 
        self.run_event.set() 

    def accept_client(self):
        client_socket, client_addr = self.server_socket.accept()
        client_name = client_socket.recv(1024).decode('utf-8')

        if client_name in self.clients.values():
            client_socket.send('Name already taken'.encode('utf-8'))
            client_socket.close()
            return False
        else:
            self.clients[client_socket] = client_name
            client_socket.send('Welcome'.encode('utf-8'))
            self.broadcast(client_socket, 'join')
            client_thread = threading.Thread(target=self.handle_client, args=(client_socket,))
            client_thread.start()
            return True

    def close_client(self, client_socket):
        if client_socket in self.clients:
            client_name = self.clients.pop(client_socket)
            try:
                client_socket.send('server-shutdown'.encode('utf-8')) 
            except BrokenPipeError:
                pass  
            client_socket.close()
            self.broadcast(None, f'User {client_name} left')
            return True
        return False

    def broadcast(self, client_socket_sent, message):
        if client_socket_sent is None:
            msg = message 
        else:
            msg = f'{self.clients[client_socket_sent]}: {message}'
        
        for client_socket in self.clients.keys():
            if client_socket != client_socket_sent:
                try:
                    client_socket.send(msg.encode('utf-8'))
                except:
                    self.close_client(client_socket)

    def shutdown(self):
        self.run_event.clear() 
        for client_socket in self.clients:
            client_socket.send('server-shutdown'.encode('utf-8'))
            client_socket.close()
        self.server_socket.close()

    def get_clients_number(self):
        return len(self.clients)

    def handle_client(self, client_socket):
        while True:
            try:
                message = client_socket.recv(1024).decode('utf-8')
                if message == 'exit':
                    self.close_client(client_socket)
                    break
                else:
                    self.broadcast(client_socket, message)
            except:
                self.close_client(client_socket)
                break

    def run(self):
        print("Server is running...")
        try:
            while True:
                self.accept_client()
        except KeyboardInterrupt:
            self.shutdown()


# ClientTCP Class
class ClientTCP:
    def __init__(self, client_name, server_port):
        self.client_name = client_name
        self.server_addr = 'localhost'
        self.server_port = server_port
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.exit_run = threading.Event()
        self.exit_receive = threading.Event()
        self.exit_run.set()
        self.exit_receive.set()
    
    def connect_server(self):
        self.client_socket.connect((self.server_addr, self.server_port))
        self.client_socket.send(self.client_name.encode('utf-8'))
        response = self.client_socket.recv(1024).decode('utf-8')
        if response == 'Welcome':
            print(f'Connected as {self.client_name}')
            return True
        else:
            print(response)
            return False

    def send(self, text):
        self.client_socket.send(text.encode('utf-8'))

    def receive(self):
         while self.exit_receive.is_set(): 
            try:
                message = self.client_socket.recv(1024).decode('utf-8')
                if message == 'server-shutdown':
                    print('Server has shut down.')
                    break
                print(message)
            except:
                break

    def run(self):
        if self.connect_server():
            recv_thread = threading.Thread(target=self.receive)
            recv_thread.start()
            try:
                while True:
                    text = input()
                    if text == 'exit':
                        self.send('exit')
                        break
                    self.send(text)
            except KeyboardInterrupt:
                print("\nExiting due to keyboard interruption.")
                self.send('exit')
            self.client_socket.close()

# ServerUDP Class
class ServerUDP:
    def __init__(self, server_port):
        self.server_port = server_port
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.server_socket.bind(('localhost', server_port))
        self.clients = {}
        self.messages = []

    def accept_client(self, client_addr, message):
        if message.startswith("join:"):
            client_name = message.split(":")[1]
            if client_name in self.clients.values():
                self.server_socket.sendto('Name already taken'.encode('utf-8'), client_addr)
                return False
            else:
                self.clients[client_addr] = client_name
                self.server_socket.sendto('Welcome'.encode('utf-8'), client_addr)
                self.broadcast(client_addr, f'User {client_name} joined')
                return True
        return False

    def close_client(self, client_addr):
        if client_addr in self.clients:
            client_name = self.clients.pop(client_addr)
            self.broadcast(client_addr, f'User {client_name} left')
            return True
        return False

    def broadcast(self, client_addr_sent, message):
        self.messages.append(message) 
        for client_addr in self.clients.keys():
            if client_addr != client_addr_sent:
                self.server_socket.sendto(message.encode('utf-8'), client_addr)

    def shutdown(self):
        for client_addr in list(self.clients.keys()):
            self.server_socket.sendto('server-shutdown'.encode('utf-8'), client_addr)
            self.close_client(client_addr)
        self.server_socket.close()

    def get_clients_number(self):
        return len(self.clients)

    def run(self):
        print("UDP Server is running...")
        try:
            while True:
                message, client_addr = self.server_socket.recvfrom(1024)
                message = message.decode('utf-8')
                if client_addr not in self.clients:
                    self.accept_client(client_addr, message)
                elif message == 'exit':
                    self.close_client(client_addr)  
                else:
                    self.broadcast(client_addr, f'{self.clients[client_addr]}: {message}')
        except KeyboardInterrupt:
            self.shutdown()


# ClientUDP Class
class ClientUDP:
    def __init__(self, client_name, server_port):
        self.client_name = client_name
        self.server_addr = 'localhost'
        self.server_port = server_port
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.exit_run = threading.Event()  
        self.exit_receive = threading.Event()  
        self.exit_run.set()  
        self.exit_receive.set() 

    def connect_server(self):
        try:
            self.client_socket.sendto(f'join:{self.client_name}'.encode('utf-8'), (self.server_addr, self.server_port))
            response, _ = self.client_socket.recvfrom(1024)
            response = response.decode('utf-8')

            if response == 'Welcome':
                print(f"Connected as {self.client_name}")
                return True
            else:
                print(f"Failed to connect: {response}")
                return False
        except Exception as e:
            print(f"Failed to connect to the server: {e}")
            return False
        
    def send(self, text):
        try:
            self.client_socket.sendto(text.encode('utf-8'), (self.server_addr, self.server_port))
        except Exception as e:
            print(f"Error sending message: {e}")

    def receive(self):
        while self.exit_receive.is_set():
            try:
                message, _ = self.client_socket.recvfrom(1024)
                message = message.decode('utf-8')
                if message == 'server-shutdown':
                    print('Server has shut down.')
                    break
                print(message)
            except Exception as e:
                print(f"Error receiving message: {e}")
                break

    def run(self):
        if self.connect_server():
            recv_thread = threading.Thread(target=self.receive)
            recv_thread.start()
            try:
                while self.exit_run.is_set():
                    text = input()  
                    if text == 'exit':  
                        self.send('exit')
                        break
                    self.send(text) 
            except KeyboardInterrupt:
                print("\nExiting due to keyboard interruption.")
                self.send('exit')
                self.exit_run.clear()
                self.exit_receive.clear()

            recv_thread.join(timeout=2)
            self.client_socket.close()


# Main for both TCP and UDP
if __name__ == "__main__":
    protocol = input("Enter 'tcp' or 'udp' for chatroom protocol: ").strip().lower()
    role = input("Enter 'server' to start as server, 'client' to start as client: ").strip()

    if protocol == 'tcp':
        if role == 'server':
            port = int(input("Enter port number for server: "))
            server = ServerTCP(port)
            server.run()
        elif role == 'client':
            port = int(input("Enter port number of the server: "))
            name = input("Enter your name: ").strip()
            client = ClientTCP(name, port)
            client.run()

    elif protocol == 'udp':
        if role == 'server':
            port = int(input("Enter port number for server: "))
            server = ServerUDP(port)
            server.run()
        elif role == 'client':
            port = int(input("Enter port number of the server: "))
            name = input("Enter your name: ").strip()
            client = ClientUDP(name, port)
            client.run()