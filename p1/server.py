import argparse
import pickle
import socket

def main():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.bind((socket.gethostname(), args.port))
    while True:
        data, addr = s.recvfrom(1024)
        print('data from', addr)
        register = pickle.loads(data)
        print('{0} wants to register at address {1} on port {2}'.format(*register))
        s.sendto(bytes('SUCCESS', 'utf-8'), addr)

parser = argparse.ArgumentParser(description='Server process that tracks teh state of clients')

parser.add_argument('--port', '-p',     type=int,
                                        default=25565,
                                        help='port to listen on.')

args = parser.parse_args()
main()
