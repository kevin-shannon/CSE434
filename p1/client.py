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
        self.host_addr = (args.host, args.host_port)
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

    def send_datagram(self, payload, addr):
        self.sock.sendto(pickle.dumps(payload), addr)
        response = pickle.loads(self.sock.recv(1024))
        print(f'{response.status} ({payload.command})')
        return response

    def handle_datagram(self, data):
        if data.command == 'set-id':
            self.i = data.args.i
            self.n = data.args.n
            self.prev = data.args.prev
            self.next = data.args.next
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
        payload = sn(command='register', args=sn(user_name=user_name, port=int(in_port)))
        response = self.send_datagram(payload, self.host_addr)
        if response.status == 'SUCCESS':
            start_new_thread(self.listen, (int(in_port),))

    def setup(self, n):
        response = self.send_datagram(sn(command='setup-dht', args=sn(n=int(n),)), self.host_addr)
        if response.status == 'SUCCESS':
            n = len(response.body)
            for i in range(1, n):
                payload = sn(command='set-id', args=sn(i=i, n=n, prev=response.body[(i-1) % n], next=response.body[(i+1) % n]))
                self.sock.sendto(pickle.dumps(payload), response.body[i].recv_addr)
            self.i = 0
            self.n = n
            self.prev = response.body[-1 % n]
            self.next = response.body[1]

            with open('StatsCountry.csv') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    record = dict(row)
                    payload = sn(command='store', args=sn(record=record))
                    self.sock.sendto(pickle.dumps(payload), self.next.recv_addr)

            self.send_datagram(sn(command='dht-complete', args=None), self.host_addr)

    def store(self, record):
        id = self.hash_table.hash_func(record['Long Name']) % self.n
        if self.i == id:
            self.hash_table.add(record)
        else:
            payload = sn(command='store', args=sn(record=record))
            self.sock.sendto(pickle.dumps(payload), self.next.recv_addr)

    def query_dht(self, long_name):
        response = self.send_datagram(sn(command='query-dht', args=None), self.host_addr)
        if response.status == 'SUCCESS':
            payload = sn(command='query', args=sn(long_name=long_name, u_addr=self.sock.getsockname()))
            record = self.send_datagram(payload, addr=response.body.recv_addr).body
            print(record)

    def query(self, long_name, u_addr):
        id = self.hash_table.hash_func(long_name) % self.n
        if self.i == id:
            record = self.hash_table.lookup(long_name)
            if record is not None:
                self.sock.sendto(pickle.dumps(sn(status='SUCCESS', body=record)), u_addr)
            else:
                err_msg = f'Long name, {long_name}, could not be found in the DHT.'
                self.sock.sendto(pickle.dumps(sn(status='FAILURE', body=err_msg)), u_addr)
        else:
            payload = sn(command='query', args=sn(long_name=long_name, u_addr=u_addr))
            self.sock.sendto(pickle.dumps(payload), self.next.recv_addr)


parser = argparse.ArgumentParser(description='Client process that tracks the state of clients')

parser.add_argument('-host',                required=True,
                                            help='ip address of host server.')
parser.add_argument('--host_port', '-hp',   type=int,
                                            default=25565,
                                            help='port to talk to server on.')

args = parser.parse_args()
User = namedtuple('User', 'user_name out_addr recv_addr')
Client()
