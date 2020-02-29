import argparse
import csv
import pickle
import socket
import sys

from _thread import start_new_thread
from collections import namedtuple
from os import getcwd
from os.path import dirname
from os.path import join
from types import SimpleNamespace as sn
from utils.HashTable import HashEntry
from utils.HashTable import HashTable


class Client:
    '''
    The Client class houses the socket object, and client info. When initialized,
    an infinite loop will start waiting for user commands. When a new user
    is registered a new thread will be spawned to listen on their receive port.
    Only one user may be registered per Client process.

    Attributes
    ----------
    sock : socket.socket
        The socket object used for communication.
    host_addr : tuple
        The address of the server.
    stat_file : str
        Path to stats file.
    hash_table : utils.HashTable.HashTable
        Client's portion of the DHT.
    i : int
        Identifier for position in DHT.
    n : int
        Number of users in the ring.
    prev : __main__.User
        The previous User.
    next : __main__.User
        The next User.

    Parameters
    ----------
    host_ip : str
        The IP address that the server is running on.
    host_port : int
        The port that the server is listening on.
    stat_file : str
        Path to stats file.
    '''

    def __init__(self, host_ip, host_port, stat_file):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.host_addr = (host_ip, host_port)
        self.stat_file = stat_file

        self.display_help()
        while True:
            command = input('enter command: ')
            self.interpret_command(command)

    def listen(self, port):
        '''
        Forever listens on the specified port. Once data is received it passes
        it on to self.handle_datagram.

        Parameters
        ----------
        port : int
            The port to listen on.
        '''
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            sock.bind((socket.gethostname(), port))
        except:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            sock.bind((s.getsockname()[0], port))
        while True:
            raw_bytes, addr = sock.recvfrom(1024)
            data = pickle.loads(raw_bytes)
            self.handle_datagram(data)

    def send_datagram(self, payload, addr):
        '''
        Used for sending something when a response is expected. This will send a
        pickle of the payload to the specified address. It will then wait for a response.
        payload should be a SimpleNamespace for it to comply with the message format.

        Parameters
        ----------
        payload : types.SimpleNamespace
            What is being sent.
        addr : tuple
            Where the payload is being sent.

        Returns
        -------
        types.SimpleNamespace
            SimpleNamespace containing a status code and a body which could be anything.
        '''
        self.sock.sendto(pickle.dumps(payload), addr)
        response = pickle.loads(self.sock.recv(1024))
        print(f'{response.status} ({payload.command})')
        return response

    def handle_datagram(self, data):
        '''
        Used for handling p2p commands recieved by the Client. Depending on the command
        it will call the appropriate function or set member variables.

        Parameters
        ----------
        data : types.SimpleNamespace
            The data that has been received.
        '''
        if data.command == 'set-id':
            self.set_id(**data.args.__dict__)
        elif data.command == 'store':
            self.store(**data.args.__dict__)
        elif data.command == 'query':
            self.query(**data.args.__dict__)
        elif data.command == 'leave':
            self.leave()
        elif data.command == 'teardown':
            self.teardown()

    def interpret_command(self, command):
        '''
        Simple function for parsing user input.

        Parameters
        ----------
        command : str
            The user sdin input.
        '''
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
            elif command_split[0] == 'query-dht':
                self.query_dht(' '.join(command_split[1:]))
            elif command_split[0] == 'leave-dht':
                self.leave_dht()
            elif command_split[0] == 'teardown-dht':
                self.teardown_dht()
            else:
                print("Command not understood, try again.")

    def display_help(self):
        '''
        Prints help menu.
        '''
        print('\nAvailable commands:')
        print('help')
        print('register <user-name> <port>')
        print('setup-dht <n>')
        print('query-dht <long-name>')
        print('leave-dht')
        print('teardown-dht')
        print('exit\n')

    def register(self, user_name, port):
        '''
        Registers a new user with the server with the desired user_name and port.
        After a successful response from the server, a thread will be spawned to
        listen on the chosen port. user_name and port should be unique across
        all Clients.

        Parameters
        ----------
        user_name : string
            Name of client, must be less than 16 characters.
        port : int
            Reasonable port that is not already in use, must be less than 65535.
        '''
        payload = sn(command='register', args=sn(user_name=user_name, port=int(port)))
        response = self.send_datagram(payload, self.host_addr)
        if response.status == 'SUCCESS':
            start_new_thread(self.listen, (int(port),))

    def setup_dht(self, n):
        '''
        Asks server for n-1 other free users then constructs a ring structure and builds
        a DHT amongst the n nodes.

        Parameters
        ----------
        n : int
            Number of nodes in the DHT, cannot exceed number of free users.
        '''
        response = self.send_datagram(sn(command='setup-dht', args=sn(n=int(n),)), self.host_addr)
        if response.status == 'SUCCESS':
            n = len(response.body)
            self.set_id(0, n, response.body[-1 % n], response.body[1])
            for i in range(1, n):
                payload = sn(command='set-id', args=sn(i=i, n=n, prev=response.body[(i-1) % n], next=response.body[(i+1) % n]))
                self.sock.sendto(pickle.dumps(payload), response.body[i].recv_addr)
            # Read Stats File
            with open(self.stat_file) as f:
                reader = csv.DictReader(f)
                for row in reader:
                    self.store(dict(row))
            # All done
            self.send_datagram(sn(command='dht-complete', args=None), self.host_addr)

    def set_id(self, i, n, prev, next):
        self.i = i
        self.n = n
        self.prev = prev
        self.next = next
        self.hash_table = HashTable(size=353)

    def store(self, record):
        '''
        If the id computed by the hash is our id then the record will be added
        to the hash table, otherwise it will be sent along the chain.

        Parameters
        ----------
        record : dict
            dictionary mapping each field associated with a particular country to its value.
        '''
        id = self.hash_table.hash_func(record['Long Name']) % self.n
        if self.i == id:
            self.hash_table.add(record)
        else:
            payload = sn(command='store', args=sn(record=record))
            self.sock.sendto(pickle.dumps(payload), self.next.recv_addr)

    def query_dht(self, long_name):
        '''
        Sends request to server to query, on a successful response it will go around the ring
        looking for who has the long_name that was queried. If found it will be printed.

        Parameters
        ----------
        long_name : str
            Long Name of Country to query DHT.
        '''
        response = self.send_datagram(sn(command='query-dht', args=None), self.host_addr)
        if response.status == 'SUCCESS':
            payload = sn(command='query', args=sn(long_name=long_name, u_addr=self.sock.getsockname()))
            record = self.send_datagram(payload, response.body.recv_addr).body
            print(record)

    def query(self, long_name, u_addr):
        '''
        If the id computed by the hash is our id then send it back to the user that
        queried, otherwise the command will be sent along the chain.

        Parameters
        ----------
        long_name : str
            Long Name of Country to query DHT.
        u_addr : tuple
            Address of the user who issued the query.
        '''
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

    def leave_dht(self):
        response = self.send_datagram(sn(command='leave-dht', args=None), self.host_addr)
        if response.status == 'SUCCESS':
            # Delete the DHT

            # Rebuild the DHT

            self.send_datagram(sn(command='dht-rebuilt', args=None), self.host_addr)

    def leave(self):
        pass

    def teardown_dht(self):
        response = self.send_datagram(sn(command='teardown-dht', args=None), self.host_addr)
        if response.status == 'SUCCESS':
            payload = sn(command='teardown', args=None)
            self.send_datagram(payload, self.next.recv_addr)
            # All done
            self.send_datagram(sn(command='teardown-complete', args=None), self.host_addr)

    def teardown(self):
        self.hash_table = None
        next = self.next
        i = self.i
        self.set_id(None, None, None, None)
        if i == 0:
            return self.sock.sendto(pickle.dumps(sn(status='SUCCESS', body=None)), self.sock.getsockname())
        payload = sn(command='teardown', args=None)
        self.sock.sendto(pickle.dumps(payload), next.recv_addr)


User = namedtuple('User', 'user_name out_addr recv_addr')

if __name__ == '__main__':
    # Useage: python3 client.py -i 100.64.15.69 --p 25565
    parser = argparse.ArgumentParser(description='Client process that tracks the state of clients')

    parser.add_argument('--host_ip', '-i',      required=True,
                                                help='ip address of host server.')
    parser.add_argument('--host_port', '-p',    type=int,
                                                default=25565,
                                                help='port to talk to server on.')
    parser.add_argument('--stat_file', '-f',    default=join(dirname(getcwd()), 'data', 'StatsCountry.csv'),
                                                help='path to stats file.')

    args = parser.parse_args()
    Client(**args.__dict__)
