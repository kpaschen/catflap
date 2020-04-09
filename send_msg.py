# Send a motion event to the catflap daemon.
# As it is now, it would be simpler to use netcat:
# echo $msg | nc localhost 3333
# use nc -u for udp

import argparse
from socket import AF_INET, socket, SOCK_DGRAM, SOCK_STREAM

if __name__ == "__main__":
    parser = argparse.ArgumentParser('send motion event')
    parser.add_argument('--host', default='127.0.0.1', help='Where the catflap daemon runs')
    parser.add_argument('--port', default=3333, help='Port of the catflap daemon')
    parser.add_argument('--msg', default=None, help='Message to send to the catflap daemon')
    parser.add_argument('--proto', default='UDP', help='Protocol (TCP or UDP)')
    args = parser.parse_args()
    if not args.msg:
        print('Skipping event with empty message')
        exit
    addr = (args.host, args.port)
    if args.proto == 'TCP':
        client_socket = socket(AF_INET, SOCK_STREAM)
        client_socket.connect(addr)
        client_socket.send(bytes(args.msg, "utf8"))
        client_socket.close()
    else:
        # udp socket
        client_socket = socket(AF_INET, SOCK_DGRAM)
        client_socket.sendto(bytes(args.msg, 'utf8'), addr)


