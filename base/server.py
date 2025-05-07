from ..util.sock import TCPSockServer as SockServer
# from ..util.sock import UDPSockServer as SockServer # UNSTABLE

import logging
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s [%(levelname)s] > %(message)s")

from miniros.util.decorators import decorators

def run(host, port):
    s = SockServer(host, port)
    @decorators.threaded()
    def run():
        s.run()
    run().join()

if __name__ == "__main__":
    run()