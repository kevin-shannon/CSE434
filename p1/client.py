import argparse
import csv
import pickle
import socket
import sys

from _thread import start_new_thread
from collections import namedtuple
from types import SimpleNamespace as sn
from utils.HashTable import HashEntry
from utils.HashTable import HashTable


class Client:
    def __init__(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.hash_table = HashTable(size=353)
        self.display_help()
        while True:
            command = input('enter command: ')
            self.interpret_command(command)

    def success(self, addr, body=None):
        self.sock.sendto(pickle.dumps(sn(status='SUCCESS', body=body)), addr)

    def failure(self, addr):
        self.sock.sendto(pickle.dumps(sn(status='FAILURE', body=None)), addr)

    def listen(self, port):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind((socket.gethostname(), port))
        while True:
            raw_bytes, addr = sock.recvfrom(1024)
            data = pickle.loads(raw_bytes)
            print('Received', data)
            self.handle_datagram(data)

    def send_datagram(self, payload, addr=None, supress=False):
        addr = addr if addr is not None else (args.host, args.host_port)
        self.sock.sendto(pickle.dumps(payload), addr)
        response = pickle.loads(self.sock.recv(1024))
        if not supress:
            print(response.status)
        return response if response.status == 'SUCCESS' else None

    def handle_datagram(self, data):
        if data.command == 'set-id':
            self.i = data.args.i
            self.n = data.args.n
            self.prev = data.args.prev
            self.next = data.args.next
            return self.success((self.prev.ipv4, self.prev.port))
        if data.command == 'store':
            self.store(data.args.record)

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

    def display_help(self):
        print('\nAvailable commands:')
        print('help')
        print('register <user-name> <port>')
        print('setup-dht <n> <user-name>')
        print('query-dht <user-name>')
        print('exit\n')

    def register(self, user_name, port):
        if self.send_datagram(sn(command='register', args=sn(user_name=user_name, port=int(port)))):
            start_new_thread(self.listen, (int(port),))

    def setup_dht(self, n, user_name):
        response = self.send_datagram(sn(command='setup-dht', args=sn(n=int(n), user_name=user_name)))
        if response:
            n = len(response.body)
            for i in range(1, n):
                payload = sn(command='set-id', args=sn(i=i, n=n, prev=response.body[(i-1) % n], next=response.body[(i+1) % n]))
                addr = (response.body[i].ipv4, response.body[i].port)
                self.send_datagram(payload=payload, addr=addr, supress = True)
            self.i = 0
            self.n = n
            self.prev = response.body[-1 % n]
            self.next = response.body[1]
            print('reading csv')

            with open('StatsCountry.csv') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    record = dict(row)
                    id = self.hash_table.hash_func(record['Long Name']) % self.n
                    if self.i == id:
                        self.hash_table.add(record)
                    else:
                        print(f'sending record to {(self.next.ipv4, self.next.port)}')
                        self.store(record)

            print('complete')
            self.send_datagram(sn(command='dht-complete', args=None))

    def store(self, record):
        id = self.hash_table.hash_func(record['Long Name']) % self.n
        if self.i == id:
            self.hash_table.add(record)
        else:
            print(f'sending record to {(self.next.ipv4, self.next.port)}')
            self.send_datagram(sn(command='store', args=sn(record=record)), (self.next.ipv4, self.next.port), supress=False)
        return self.success((self.prev.ipv4, self.prev.port))


parser = argparse.ArgumentParser(description='Client process that tracks teh state of clients')

parser.add_argument('-host',                required=True,
                                            help='ip address of host server.')
parser.add_argument('--host_port', '-hp',   type=int,
                                            default=25565,
                                            help='port to talk to server on.')

args = parser.parse_args()
User = namedtuple('User', 'user_name ipv4 port')
Client()
