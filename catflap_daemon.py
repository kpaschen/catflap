import argparse
import asyncio

class UDPServerProtocol(asyncio.DatagramProtocol):

    def datagram_received(self, data, addr):
        message = data.decode('utf8')
        print('received message {0}'.format(message))


class TCPServerProtocol(asyncio.Protocol):

    def connection_made(self, transport):
        self.transport = transport

    def data_received(self, data):
        msg = data.decode('utf8')
        print('received message {0}'.format(msg))
        self.transport.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser('start the cat flap daemon')
    parser.add_argument('--host', default='127.0.0.1', help='Where the catflap daemon runs')
    parser.add_argument('--port', default=3333, help='Port of the catflap daemon')
    parser.add_argument('--proto', default='UDP', help='Protocol (TCP or UDP)')
    args = parser.parse_args()
    loop = asyncio.get_event_loop()
    if args.proto == 'TCP':
        connect = loop.create_server(lambda: TCPServerProtocol(),
                args.host, args.port)
        server = loop.run_until_complete(connect)
        loop.run_forever()
    else:
        connect = loop.create_datagram_endpoint(
                lambda: UDPServerProtocol(),
                local_addr=(args.host, args.port))
        server, _ = loop.run_until_complete(connect)
        loop.run_forever()
