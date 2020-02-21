import argparse
import pickle
import random
import socket

from collections import namedtuple
from types import SimpleNamespace as sn


class Server:
    '''
    The server class holds state information about clients and responds to requests
    from the clients.

    Attributes
    ----------
    users : dict
        Collection of all register users, maps user_name to User namedtuple.
    state : dict
        Maps user_name to their staet {'Free', 'InDHT', 'Leader'}.
    num_DHTs : int
        Number of DHT's constructed, should be limited to 1.
    sock : socket.socket
        The socket object used for communication.
    out_addr : tuple
        Address of the last client we've recieved a message from.

    Parameters
    ----------
    port : int
        Port to listen on.
    '''

    def __init__(self, port):
        self.users = {}
        self.state = {}
        self.num_DHTs = 0
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind((socket.gethostname(), port))
        while True:
            bytes, self.out_addr = self.sock.recvfrom(1024)
            print('Received data from', self.out_addr)
            data = pickle.loads(bytes)
            self.handle_datagram(data)

    def failure(self):
        '''
        Sends a FAILURE response to self.out_addr.
        '''
        self.sock.sendto(pickle.dumps(sn(status='FAILURE', body=None)), self.out_addr)

    def success(self, body=None):
        '''
        Sends a SUCCESS response to self.out_addr.

        Parameters
        ----------
        body : any
            Data relevant to response.
        '''
        self.sock.sendto(pickle.dumps(sn(status='SUCCESS', body=body)), self.out_addr)

    def lookup(self):
        '''
        Attempts to find user in list of registered users who has the same out_addr.

        Returns
        -------
        str or None
            If user is found it will return their user_name otherwise it will return None.
        '''
        for user in self.users:
            if self.users[user].out_addr == self.out_addr:
                return user
        return None

    def handle_datagram(self, data):
        '''
        Used for handling commands from a client. Depending on the command
        it will take the appropriate actions to respond.

        Parameters
        ----------
        data : types.SimpleNamespace
            The data that has been received from the client.
        '''
        if data.command == 'register':
            if len(data.args.user_name) > MAX_USR_LEN or data.args.port > MAX_PORT:
                return self.failure()
            user = User(data.args.user_name, self.out_addr, (self.out_addr[0], data.args.port))
            # Check if any fields are identical to any fields already registered
            for field in User._fields:
                for name in self.users:
                    if self.users[name].__getattribute__(field) == user.__getattribute__(field):
                        return self.failure()
            # User is unique and valid, add to registered users
            self.users[data.args.user_name] = user
            self.state[data.args.user_name] = FREE
            print(f'Successfully registered user: {user}')
            return self.success()
        elif data.command == 'setup-dht':
            leader = self.lookup()
            if (self.users.get(leader) is None or data.args.n < 2
                or len(self.users) < data.args.n or self.num_DHTs > 0):
                return self.failure()
            # Begin setup of DHT
            self.state[leader] = LEADER
            dht_users = [leader]
            for _ in range(1, data.args.n):
                random_free_user = random.choice([user for user in self.state if self.state[user] == FREE])
                dht_users.append(random_free_user)
                self.state[random_free_user] = IN_DHT
            self.num_DHTs += 1
            self.success(body=[self.users[user] for user in dht_users])
            # Wait for Leader to send dht-complete
            while True:
                bytes, self.out_addr = self.sock.recvfrom(1024)
                print('Received data from', self.out_addr)
                data = pickle.loads(bytes)
                if data.command == 'dht-complete' and self.lookup() == leader:
                    return self.success()
                else:
                    return self.failure()
        elif data.command == 'query-dht':
            if self.num_DHTs == 0:
                return self.failure()
            user = self.lookup()
            if user is None or self.state[user] != FREE:
                return self.failure()
            # User is authorized to issue a query
            random_user = random.choice([user for user in self.state if self.state[user] != FREE])
            return self.success(self.users[random_user])


FREE = 'Free'
IN_DHT = 'InDHT'
LEADER = 'Leader'
MAX_PORT = 65535
MAX_USR_LEN = 15
User = namedtuple('User', 'user_name out_addr recv_addr')

if __name__ == '__main__':
    # Useage: python3 server.py --port 25565
    parser = argparse.ArgumentParser(description='Server process that tracks the state of clients')

    parser.add_argument('--port', '-p',     type=int,
                                            default=25565,
                                            help='port to listen on.')

    args = parser.parse_args()
    Server(**args.__dict__)
