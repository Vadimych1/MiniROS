from ..util.sock import TCPSockServer as SockServer
# from ..util.sock import UDPSockServer as SockServer # UNSTABLE

import logging
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s [%(levelname)s] > %(message)s")

from util.threads import threaded

if __name__ == "__main__":
    s = SockServer("localhost", 3000)

    @threaded()
    def run():
        s.run()

    run().join()