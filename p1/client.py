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
from utils.HashTable import Record


class Client:
    def __init__(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.hash_table = HashTable(size=353)
        self.display_help()
        while True:
            command = input('enter command: ')
            self.interpret_command(command)

    def listen(self, port):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind((socket.gethostname(), port))
        while True:
            raw_bytes, addr = sock.recvfrom(1024)
            data = pickle.loads(raw_bytes)
            self.handle_datagram(data)

    def send_datagram(self, payload, addr=(args.host, args.host_port), supress=False):
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
        if data.command == 'store':
            self.store(data)
        if data.command == 'dht-complete':
            self.dht_complete()

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
        print('setup-dht <n>')
        print('query-dht <user-name>')
        print('exit\n')

    def register(self, user_name, ipv4, port):
        if send_datagram(sn(command='register', args=sn(user_name=user_name, ipv4=ipv4, port=int(port)))):
            self.start_new_thread(self.listen, (int(port),))

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

            with open('StatsCountry.csv') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    record = dict(row)
                    self.store(record)

    def store(self, record):
        id = self.hash_table.hash_func(record['Long Name']) % self.n
        if self.i == id:
            self.hash_table.add(record)
        else:
            self.send_datagram(sn(command='store', args=sn(record=record)), (self.next.ipv4, self.next.port), supress=True)


    def dht_complete(self):
        request = sn(command='dht-complete', args=sn(user_name=user_name))
        self.sock.sendto(pickle.dumps(request), (args.host, args.host_port))
        response = self.sock.recv(1024)
        data = pickle.loads(response)
        print(data.status)

parser = argparse.ArgumentParser(description='Client process that tracks teh state of clients')

parser.add_argument('-host',                required=True,
                                            help='ip address of host server.')
parser.add_argument('--host_port', '-hp',   type=int,
                                            default=25565,
                                            help='port to talk to server on.')

args = parser.parse_args()
User = namedtuple('User', 'user_name ipv4 port')
Client()
