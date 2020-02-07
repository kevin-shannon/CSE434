import argparse
import pickle
import socket
import sys

from types import SimpleNamespace as sn

def main():
    display_help()
    while True:
        command = input('enter command: ')
        interpret_command(command)

def interpret_command(command):
    if command == 'exit':
        sys.exit(0)
    elif command == 'help':
        display_help()
    else:
        command_split = command.split(' ')
        if command_split[0] == 'register':
            register(*command_split[1:])
        else:
            print("Command not understood, try again.")

def display_help():
    print('Available commands:')
    print('help')
    print('register <user-name> <IPv4-address> <port>')
    print('setup-dht <n> <user-name>')
    print('query-dht <user-name>')
    print('exit\n')

def register(user_name, ipv4, port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    request = sn(command='register', args=sn(user_name=user_name, ipv4=ipv4, port=int(port)))
    sock.sendto(pickle.dumps(request), (args.host, args.host_port))
    response = sock.recv(1024)
    data = pickle.loads(response)
    print(data.status)


parser = argparse.ArgumentParser(description='Client process that tracks teh state of clients')

parser.add_argument('-host',                required=True,
                                            help='ip address of host server.')
parser.add_argument('--host_port', '-hp',   type=int,
                                            default=25565,
                                            help='port to talk to server on.')

args = parser.parse_args()
main()
