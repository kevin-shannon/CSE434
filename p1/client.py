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
        self.sock.sendto(pickle.dumps(sn(type='response', status='SUCCESS', body=body)), addr)

    def failure(self, addr):
        self.sock.sendto(pickle.dumps(sn(type='response', status='FAILURE', body=None)), addr)

    def listen(self, port):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind((socket.gethostname(), port))
        while True:
            raw_bytes, addr = sock.recvfrom(1024)
            data = pickle.loads(raw_bytes)
            self.handle_datagram(data)

    def send_datagram(self, payload, addr=None, suppress=False):
        addr = addr if addr is not None else (args.host, args.host_port)
        self.sock.sendto(pickle.dumps(payload), addr)
        response = pickle.loads(self.sock.recv(1024))
        if not suppress:
            print(response.status)
        return response if response.status == 'SUCCESS' else None

    def handle_datagram(self, data):
        if data.type == 'response':
            return
        if data.command == 'set-id':
            self.i = data.args.i
            self.n = data.args.n
            self.prev = data.args.prev
            self.next = data.args.next
            return self.success(self.prev.addr)
        if data.command == 'store':
            self.store(data.args.record)
        if data.command == 'query':
            self.query(data.args.long_name, data.args.u_addr)

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
                self.setup(*command_split[1:])
            elif command_split[0] == 'query-dht':
                self.query_dht(' '.join(command_split[1:]))
            else:
                print("Command not understood, try again.")

    def display_help(self):
        print('\nAvailable commands:')
        print('help')
        print('register <user-name> <port>')
        print('setup-dht <n>')
        print('query-dht <long-name>')
        print('exit\n')

    def register(self, user_name, in_port):
        user = self.send_datagram(sn(command='register', args=sn(user_name=user_name, in_port=int(in_port))))
        if user:
            start_new_thread(self.listen, (int(in_port),))

    def setup(self, n):
        response = self.send_datagram(sn(command='setup-dht', args=sn(n=int(n),)))
        if response:
            n = len(response.body)
            for i in range(1, n):
                payload = sn(type='request', command='set-id', args=sn(i=i, n=n, prev=response.body[(i-1) % n], next=response.body[(i+1) % n]))
                self.send_datagram(payload=payload, addr=(response.body[i].addr.ipv4, response.body[i].in_port), suppress=True)
            self.i = 0
            self.n = n
            self.prev = response.body[-1 % n]
            self.next = response.body[1]

            with open('StatsCountry.csv') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    record = dict(row)
                    self.send_datagram(sn(type='request', command='store', args=sn(record=record)), addr=(self.next.addr.ipv4, self.next.in_port), suppress=True)

            self.send_datagram(sn(command='dht-complete', args=None), suppress=True)

    def store(self, record):
        id = self.hash_table.hash_func(record['Long Name']) % self.n
        if self.i == id:
            self.hash_table.add(record)
        else:
            self.send_datagram(sn(type='request', command='store', args=sn(record=record)), addr=(self.next.addr.ipv4, self.next.in_port), suppress=True)
        return self.success(self.prev.addr)

    def query_dht(self, long_name):
        response = self.send_datagram(sn(command='query-dht', args=None))
        if response:
            record = self.send_datagram(sn(type='request', command='query', args=sn(long_name=long_name, u_addr=self.sock.getsockname())), addr=(response.body.addr.ipv4, response.body.in_port), suppress=True)
            print(record)

    def query(self, long_name, u_addr):
        id = self.hash_table.hash_func(long_name) % self.n
        print(self.i, id)
        if self.i == id:
            record = self.hash_table.lookup(long_name)
            return self.success(u_addr, body=record)
        else:
            response = self.send_datagram(sn(type='request', command='query', args=sn(long_name=long_name, u_addr=u_addr)), addr=(self.next.addr.ipv4, self.next.in_port), suppress=True)
            return self.success(self.prev.addr)



parser = argparse.ArgumentParser(description='Client process that tracks the state of clients')

parser.add_argument('-host',                required=True,
                                            help='ip address of host server.')
parser.add_argument('--host_port', '-hp',   type=int,
                                            default=25565,
                                            help='port to talk to server on.')

args = parser.parse_args()
User = namedtuple('User', 'user_name addr in_port')
Addr = namedtuple('Addr', 'ipv4 port')
Client()
