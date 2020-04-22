import argparse
import asyncio
from datetime import datetime
from cat_detector import CatDetector
from trainer import Trainer

class UDPServerProtocol(asyncio.DatagramProtocol):

    def __init__(self, queue):
        self._queue = queue

    def datagram_received(self, data, addr):
        message = data.decode('utf8')
        print('received message {0}'.format(message), flush=True)
        self._queue.put_nowait(message)


class TCPServerProtocol(asyncio.Protocol):

    def __init__(self, queue):
        self._queue = queue

    def connection_made(self, transport):
        self.transport = transport

    def data_received(self, data):
        msg = data.decode('utf8')
        print('received message {0}'.format(msg), flush=True)
        self.transport.close()
        self._queue.put_nowait(message)


async def motion_worker(queue, detector):
    lastmsgtime = datetime.now()
    while True:
        msg = await queue.get()
        queue.task_done()
        msgtime = datetime.now()
        timestr = msgtime.strftime("%Y-%m-%d-%H:%M:%S")
        if (msgtime - lastmsgtime).seconds > 300:
            print("{0} time passed since last message, resetting cat detector".format(msgtime - lastmsgtime))
            detector.reset()
        try:
          value = detector.parse_message(msg)
          print("{0}: {1}".format(timestr, value), flush=True)
        except Exception as ex:
          print('Failed to parse message {0} because {1}'.format(msg, ex), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser('start the cat flap daemon')
    parser.add_argument('--host', default='127.0.0.1', help='Where the catflap daemon runs')
    parser.add_argument('--port', default=3333, help='Port of the catflap daemon')
    parser.add_argument('--proto', default='UDP', help='Protocol (TCP or UDP)')
    parser.add_argument('--statmodel', default='./catflapmodel.knn', help='Statistical model to load')
    # In opencv 4.0.0 there is no way that I can see to load a trained knn model in python.
    # But since the current model is pretty simple, we can just train it here.
    # Takes a lot less time than recompiling opencv on the pi.
    parser.add_argument('--labelfile', default=None, help='Training data for training model')
    args = parser.parse_args()
    print('Starting cat flap daemon', flush=True)
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
        print('Bringing up udp server ...', flush=True)
        server, _ = loop.run_until_complete(connect)
        print('Listening on port %d' % args.port, flush=True)
    detector = CatDetector(args.statmodel, args.labelfile)
    print('made a cat detector', flush=True)
    task = asyncio.ensure_future(motion_worker(motion_queue, detector))
    # Alternative, less low-level.
    # task = loop.create_task(motion_worker(motion_queue, detector))
    loop.run_forever()
