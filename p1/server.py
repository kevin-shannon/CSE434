import argparse
import pickle
import socket

from collections import namedtuple
from types import SimpleNamespace as sn

class Server:
    def __init__(self):
        self.registered_users = []
        self.User = namedtuple('User', 'user_name ipv4 port')
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind((socket.gethostname(), args.port))
        while True:
            self.bytes, self.addr = self.sock.recvfrom(1024)
            print('data from', self.addr)
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
            for user, ipv4, port in self.registered_users:
                if self.data.args.user_name == user or self.data.args.port == port:
                    return self.failure()

            self.registered_users.append(self.User(**self.data.args.__dict__))
            self.success()
            print('registered users:', self.registered_users)



parser = argparse.ArgumentParser(description='Server process that tracks teh state of clients')

parser.add_argument('--port', '-p',     type=int,
                                        default=25565,
                                        help='port to listen on.')

args = parser.parse_args()
Server()
