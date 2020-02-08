import argparse
import pickle
import socket
import sys

from _thread import start_new_thread
from collections import namedtuple
from types import SimpleNamespace as sn

class Client:
    def __init__(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.display_help()
        while True:
            command = input('enter command: ')
            self.interpret_command(command)

    def listen(self, port):
        print('listening...')
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind((socket.gethostname(), port))
        while True:
            raw_bytes, addr = sock.recvfrom(1024)
            data = pickle.loads(raw_bytes)
            self.handle_datagram(data)

    def handle_datagram(self, data):
        print('handeling...')
        if data.command == 'set-id':
            self.i = data.args.i
            self.n = data.args.n
            self.prev = data.args.prev
            self.next = data.args.next

    def interpret_command(self, command):
        if command == 'exit':
            sys.exit(0)
        elif command == 'help':
            self.display_help()
        else:
            command_split = command.split(' ')
            if command_split[0] == 'register':
                self.register(*command_split[1:])
            elif command_split[0] == 'setup-dht':
                self.setup_dht(*command_split[1:])
            else:
                print("Command not understood, try again.")
                print(self.next, self.prev)

    def display_help(self):
        print('\nAvailable commands:')
        print('help')
        print('register <user-name> <IPv4-address> <port>')
        print('setup-dht <n> <user-name>')
        print('query-dht <user-name>')
        print('exit\n')

    def register(self, user_name, ipv4, port):
        request = sn(command='register', args=sn(user_name=user_name, ipv4=ipv4, port=int(port)))
        self.sock.sendto(pickle.dumps(request), (args.host, args.host_port))
        response = self.sock.recv(1024)
        data = pickle.loads(response)
        print(data.status)
        if data.status == 'SUCCESS':
            start_new_thread(self.listen, (int(port),))

    def setup_dht(self, n, user_name):
        request = sn(command='setup-dht', args=sn(n=int(n), user_name=user_name))
        self.sock.sendto(pickle.dumps(request), (args.host, args.host_port))
        response = self.sock.recv(1024)
        data = pickle.loads(response)
        print(data.status)
        n = len(data.body)
        for i in range(1, n):
            request = sn(command='set-id', args=sn(i=i, n=n, prev=data.body[(i-1) % n], next=data.body[(i+1) % n]))
            self.sock.sendto(pickle.dumps(request), (data.body[i].ipv4, data.body[i].port))
        self.i = 0
        self.n = n
        self.prev = data.body[-1 % n]
        self.next = data.body[1]

parser = argparse.ArgumentParser(description='Client process that tracks teh state of clients')

parser.add_argument('-host',                required=True,
                                            help='ip address of host server.')
parser.add_argument('--host_port', '-hp',   type=int,
                                            default=25565,
                                            help='port to talk to server on.')

args = parser.parse_args()
User = namedtuple('User', 'user_name ipv4 port')
Client()
