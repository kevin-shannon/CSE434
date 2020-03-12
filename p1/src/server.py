'''
File name :   server.py
Author :      Kevin Shannon
Date :        02/29/2020
Description : This script represents a server process. Clients send commands to
              the server, the server keeps track of state information and responds
              back to the clients. This process will run indefinitly as would any
              server.
'''
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
            self.handle_segment(data)

    def failure(self):
        '''
        Sends a FAILURE response to self.out_addr.
        '''
        self.sock.sendto(pickle.dumps(sn(status=FAILURE, body=None)), self.out_addr)

    def success(self, body=None):
        '''
        Sends a SUCCESS response to self.out_addr.

        Parameters
        ----------
        body : any
            Data relevant to response.
        '''
        self.sock.sendto(pickle.dumps(sn(status=SUCCESS, body=body)), self.out_addr)

    def lookup(self, user=None):
        '''
        Attempts to find user within its list of registered users. If user isn't
        given then it will match against self.out_addr.

        Parameters
        ----------
        user : __main__.User (optional)
            User to lookup.

        Returns
        -------
        str or None
            If user is found it will return their user_name otherwise it will return None.
        '''
        if user is None:
            for user_name in self.users:
                if self.users[user_name].out_addr == self.out_addr:
                    return user_name
            return None
        else:
            for user_name in self.users:
                if self.users[user_name] == user:
                    return user_name
            return None

    def wait_until(self, command, user):
        '''
        Wait until a certain command is recieved from a certain user.

        Parameters
        ----------
        command : str
            The name of the command to wait for.
        user  str
            The user_name of the user to wait for.
        Returns
        -------
        types.SimpleNamespace
            data recieved with the command.
        '''
        while True:
            bytes, self.out_addr = self.sock.recvfrom(1024)
            print('Received data from', self.out_addr)
            data = pickle.loads(bytes)
            if data.command == command and self.lookup() == user:
                self.success()
                return data
            else:
                self.failure()

    def handle_segment(self, data):
        '''
        Used for handling commands from a client. Depending on the command
        it will call the appropriate function to process it.

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
        '''
        Registers a new user by updating the server's state.

        Parameters
        ----------
        user_name : str
            Name of the new user.
        port : int
            Port that the new user will listen on.
        '''
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
        '''
        Handles request for setting up a new dht. Assigns user's new roles. Sends
        back these new rules to the leader for them to finish the setup. Then waits
        for the leader to give an all clear before accepting any other commands.

        Parameters
        ----------
        n : int
            Size of the DHT.
        '''
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
        '''
        If the user is able to query, this will send back a random user that the
        query will start at.
        '''
        if self.num_DHTs == 0:
            return self.failure()
        user = self.lookup()
        if user is None or self.state[user] != FREE:
            return self.failure()
        # User is authorized to issue a query
        random_user = random.choice([user for user in self.state if self.state[user] != FREE])
        self.success(self.users[random_user])

    def leave_dht(self):
        '''
        If the user is allowed to leave the DHT it will tell them. Wait for a signal
        that the new DHT is built then will update states of the new leader and the
        user that left.
        '''
        state_values = list(self.state.values())
        if self.num_DHTs == 0 or state_values.count(LEADER) + state_values.count(IN_DHT) <= 2:
            return self.failure()
        user = self.lookup()
        # Verify user is registered and in the DHT
        if user is None or self.state[user] == FREE:
            return self.failure()
        self.success()
        # Wait for confirmation DHT is rebuilt
        data = self.wait_until(command='dht-rebuilt', user=user)
        # Update state
        self.state[user] = FREE
        self.state[self.lookup(data.args.leader)] = LEADER
        print(f'{user} successfully left the DHT')

    def deregister(self):
        '''
        Removes the user information from the server's state information.
        '''
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
        '''
        If the user is able to teardown the DHT then it tells the user. Then it
        waits for signal that the teardown is complete before setting all users
        to be free.
        '''
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
SUCCESS = 'SUCCESS'
FAILURE = 'FAILURE'
User = namedtuple('User', 'user_name out_addr recv_addr')

if __name__ == '__main__':
    # Useage: python3 server.py --port 25565
    parser = argparse.ArgumentParser(description='Server process that tracks the state of clients')

    parser.add_argument('--port', '-p',     type=int,
                                            default=25565,
                                            help='port to listen on.')

    args = parser.parse_args()
    Server(**args.__dict__)
