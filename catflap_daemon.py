import argparse
import asyncio
from cat_detector import CatDetector

class UDPServerProtocol(asyncio.DatagramProtocol):

    def __init__(self, queue):
        self._queue = queue

    def datagram_received(self, data, addr):
        message = data.decode('utf8')
        print('received message {0}'.format(message))
        self._queue.put_nowait(message)


class TCPServerProtocol(asyncio.Protocol):

    def __init__(self, queue):
        self._queue = queue

    def connection_made(self, transport):
        self.transport = transport

    def data_received(self, data):
        msg = data.decode('utf8')
        print('received message {0}'.format(msg))
        self.transport.close()
        self._queue.put_nowait(message)


async def motion_worker(queue, detector):
    while True:
        msg = await queue.get()
        queue.task_done()
        value = detector.parse_message(msg)
        print(value)


if __name__ == "__main__":
    parser = argparse.ArgumentParser('start the cat flap daemon')
    parser.add_argument('--host', default='127.0.0.1', help='Where the catflap daemon runs')
    parser.add_argument('--port', default=3333, help='Port of the catflap daemon')
    parser.add_argument('--proto', default='UDP', help='Protocol (TCP or UDP)')
    parser.add_argument('--statmodel', default='./catflapmodel.knn', help='Statistical model to load')
    args = parser.parse_args()
    loop = asyncio.get_event_loop()
    motion_queue = asyncio.Queue()
    if args.proto == 'TCP':
        connect = loop.create_server(lambda: TCPServerProtocol(motion_queue),
                args.host, args.port)
        server = loop.run_until_complete(connect)
    else:
        connect = loop.create_datagram_endpoint(
                lambda: UDPServerProtocol(motion_queue),
                local_addr=(args.host, args.port))
        server, _ = loop.run_until_complete(connect)
    detector = CatDetector(args.statmodel)
    task = asyncio.ensure_future(motion_worker(motion_queue, detector))
    # Alternative, less low-level.
    # task = loop.create_task(motion_worker(motion_queue, detector))
    loop.run_forever()
