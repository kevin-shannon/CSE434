import argparse
import pickle
import random
import socket

from collections import namedtuple
from types import SimpleNamespace as sn

User = namedtuple('User', 'user_name ipv4 port')

class Server:
    def __init__(self):
        self.registered_users = {}
        self.user_state = {}
        self.num_DHTs = 0
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind((socket.gethostname(), args.port))
        while True:
            self.bytes, self.addr = self.sock.recvfrom(1024)
            print('Receiving data from', self.addr)
            self.data = pickle.loads(self.bytes)
            self.handle_datagram()


    def failure(self):
        data = sn(status='FAILURE', body=None)
        self.sock.sendto(pickle.dumps(data), self.addr)

    def success(self, body=None):
        data = sn(status='SUCCESS', body=body)
        self.sock.sendto(pickle.dumps(data), self.addr)

    def handle_datagram(self):
        if self.data.command == 'register':
            if self.data.args.ipv4 != self.addr[0] or self.data.args.port > 65535 or len(self.data.args.user_name) > 15:
                return self.failure()
            for user in self.registered_users:
                if user == self.data.args.user_name or self.registered_users[user].port == self.data.args.port:
                    return self.failure()
            # User is unique and valid, add to registered users
            self.registered_users[self.data.args.user_name] = User(**self.data.args.__dict__)
            self.user_state[self.data.args.user_name] = 'Free'
            print(f'Successfully registered user: {User(**self.data.args.__dict__)}')
            self.success()
        elif self.data.command == 'setup-dht':
            if (self.registered_users.get(self.data.args.user_name) is None or self.data.args.n < 2
                or len(self.registered_users) < self.data.args.n or self.num_DHTs > 0):
                return self.failure()
            # Begin setup of DHT
            self.user_state[self.data.args.user_name] = 'Leader'
            dht_users = [self.data.args.user_name]
            for _ in range(1, self.data.args.n):
                random_free_user = random.choice([user for user in self.user_state if self.user_state[user] == 'Free'])
                dht_users.append(random_free_user)
                self.user_state[random_free_user] = 'InDHT'
            self.num_DHTs += 1
            self.success(body=[self.registered_users[user] for user in dht_users])


parser = argparse.ArgumentParser(description='Server process that tracks teh state of clients')

parser.add_argument('--port', '-p',     type=int,
                                        default=25565,
                                        help='port to listen on.')

args = parser.parse_args()
Server()
