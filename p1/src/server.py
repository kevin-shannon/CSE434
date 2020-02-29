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
        try:
            self.sock.bind((socket.gethostname(), port))
        except:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            self.sock.bind((s.getsockname()[0], port))
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

    def wait_until(self, command, user):
        while True:
            bytes, self.out_addr = self.sock.recvfrom(1024)
            print('Received data from', self.out_addr)
            data = pickle.loads(bytes)
            if data.command == command and self.lookup() == user:
                return self.success()
            else:
                self.failure()

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
            self.register(**data.args.__dict__)
        elif data.command == 'setup-dht':
            self.setup_dht(**data.args.__dict__)
        elif data.command == 'query-dht':
            self.query_dht()
        elif data.command == 'leave-dht':
            self.leave_dht()
        elif data.command == 'deregister':
            self.deregister()
        elif data.command == 'teardown-dht':
            self.teardown_dht()

    def register(self, user_name, port):
        if len(user_name) > MAX_USR_LEN or port > MAX_PORT:
            return self.failure()
        user = User(user_name, self.out_addr, (self.out_addr[0], port))
        # Check if any fields are identical to any fields already registered
        for field in User._fields:
            for name in self.users:
                if self.users[name].__getattribute__(field) == user.__getattribute__(field):
                    return self.failure()
        # User is unique and valid, add to registered users
        self.users[user_name] = user
        self.state[user_name] = FREE
        self.success()
        print(f'Successfully registered user: {user}')

    def setup_dht(self, n):
        leader = self.lookup()
        if (self.users.get(leader) is None or n < 2 or len(self.users) < n or self.num_DHTs > 0):
            return self.failure()
        # Begin setup of DHT
        self.state[leader] = LEADER
        dht_users = [leader]
        for _ in range(1, n):
            random_free_user = random.choice([user for user in self.state if self.state[user] == FREE])
            dht_users.append(random_free_user)
            self.state[random_free_user] = IN_DHT
        self.num_DHTs += 1
        self.success(body=[self.users[user] for user in dht_users])
        # Wait for Leader to send dht-complete
        self.wait_until(command='dht-complete', user=leader)
        print(f'Successfully built DHT with {dht_users}')

    def query_dht(self):
        if self.num_DHTs == 0:
            return self.failure()
        user = self.lookup()
        if user is None or self.state[user] != FREE:
            return self.failure()
        # User is authorized to issue a query
        random_user = random.choice([user for user in self.state if self.state[user] != FREE])
        return self.success(self.users[random_user])

    def leave_dht(self):
        if self.num_DHTs == 0:
            return self.failure()
        user = self.lookup()
        # Verify user is registered and in the DHT
        if user is None or self.state[user] == FREE:
            return self.failure()
        self.success()
        # Wait for confirmation dht is rebuilt
        self.wait_until(command='dht-rebuilt', user=user)

    def deregister(self):
        user = self.lookup()
        # Verify user is registered and in the DHT
        if user is None or self.state[user] != FREE:
            return self.failure()
        # Delete user's state information
        self.users.pop(user)
        self.state.pop(user)
        self.success()
        print(f'Successfully purged user {user}')


    def teardown_dht(self):
        if self.num_DHTs == 0:
            return self.failure()
        user = self.lookup()
        # Verify user is registered and in the DHT
        if user is None or self.state[user] != LEADER:
            return self.failure()
        self.success()
        self.wait_until(command='teardown-complete', user=user)
        # Free all users and decrement the number of DHTs
        for user in self.state:
            self.state[user] = FREE
        self.num_DHTs -= 1
        print(f'Successfully deleted DHT')


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
