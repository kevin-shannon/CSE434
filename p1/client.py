import argparse
import pickle
import socket
import sys

def main():
    display_help()
    while True:
        command = raw_input('enter command: ')
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
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.sendto(pickle.dumps((user_name, ipv4, port)), (args.host, args.host_port))
    data = s.recv(1024)
    print(data.decode('utf-8'))


parser = argparse.ArgumentParser(description='Client process that tracks teh state of clients')

parser.add_argument('-host',                required=True,
                                            help='ip address of host server.')
parser.add_argument('--host_port', '-hp',   type=int,
                                            default=25565,
                                            help='port to talk to server on.')

args = parser.parse_args()
main()
