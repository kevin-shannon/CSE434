import argparse
import pickle
import random
import socket

from collections import namedtuple
from types import SimpleNamespace as sn

class Server:
    def __init__(self):
        self.users = {}
        self.state = {}
        self.blocking = False
        self.num_DHTs = 0
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind((socket.gethostname(), args.port))
        while True:
            bytes, self.addr = self.sock.recvfrom(1024)
            print('Receiving data from', self.addr)
            self.data = pickle.loads(bytes)
            self.handle_datagram()

    def failure(self):
        self.sock.sendto(pickle.dumps(sn(status='FAILURE', body=None)), self.addr)

    def success(self, body=None):
        self.sock.sendto(pickle.dumps(sn(status='SUCCESS', body=body)), self.addr)

    def lookup(self):
        for user in self.users:
            if self.users[user].addr == self.addr:
                return user
        return self.failure()

    def handle_datagram(self):
        if self.data.command == 'register':
            if len(self.data.args.user_name) > 15:
                return self.failure()
            user = User(**self.data.args.__dict__, addr=Addr(*self.addr))
            if user in self.users:
                return self.failure()
            # User is unique and valid, add to registered users
            self.users[self.data.args.user_name] = user
            self.state[self.data.args.user_name] = 'Free'
            print(f'Successfully registered user: {user}')
            self.success()
        elif self.data.command == 'setup-dht':
            self.leader = self.lookup()
            if (self.users.get(self.leader) is None or self.data.args.n < 2
                or len(self.users) < self.data.args.n or self.num_DHTs > 0):
                print('failed prelim')
                return self.failure()
            # Begin setup of DHT
            self.state[self.leader] = 'Leader'
            dht_users = [self.leader]
            for _ in range(1, self.data.args.n):
                random_free_user = random.choice([user for user in self.state if self.state[user] == 'Free'])
                dht_users.append(random_free_user)
                self.state[random_free_user] = 'InDHT'
            self.num_DHTs += 1
            print(self.users)
            self.success(body=[self.users[user] for user in dht_users])
            while True:
                bytes, self.addr = self.sock.recvfrom(1024)
                print('Receiving data from', self.addr)
                self.data = pickle.loads(bytes)
                if self.data.command == 'dht-complete' and self.lookup() == self.leader:
                    return self.success()
                else:
                    return self.failure()


parser = argparse.ArgumentParser(description='Server process that tracks the state of clients')

parser.add_argument('--port', '-p',     type=int,
                                        default=25565,
                                        help='port to listen on.')

args = parser.parse_args()
User = namedtuple('User', 'user_name addr in_port')
Addr = namedtuple('Addr', 'ipv4 port')
Server()
