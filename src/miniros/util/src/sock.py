import socket, struct
import logging
from typing import Callable
import json
import asyncio
import random
import traceback
from .sock_types import *
import lz4.frame
from asyncio import Queue


# logging.basicConfig(level=logging.DEBUG)


def new_sock(use_udp: bool = False) -> socket.socket:
    """
    Initializes new fast socket
    :param
    """

    sock = None
    if "AF_UNIX" in socket.__dict__ and False:  # TODO: fix unix sockets
        sock = socket.socket(
            socket.AF_UNIX, socket.SOCK_DGRAM if use_udp else socket.SOCK_STREAM
        )

    else:
        sock = socket.socket(
            socket.AF_INET, socket.SOCK_DGRAM if use_udp else socket.SOCK_STREAM
        )

    # sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1) if not use_udp else ...
    # sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 1024 * 1024 * 32) # we do not need these
    # sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 1024 * 1024 * 32) # anymore
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    # sock.setblocking(False)

    return sock


class AsyncDistributedServer:
    """
    Async TCP server class

    Allows adding a "udp_addr" property to each tcp connection which can be requested by other clients.

    Requested address can be used on clients to send ANON messages to other clients directly
    """

    def __init__(self, ip: str, port: int):
        self.ip = ip
        self.port = port
        self.servers: dict[str, Connection] = {}

        self.sock = None
        self.running = asyncio.Event()

    async def run(self) -> None:
        self.sock: asyncio.Server = await asyncio.start_server(
            self.tcp_handler, self.ip, self.port
        )

        self.running.set()

        try:
            await self.sock.serve_forever()

        except asyncio.CancelledError:
            self.sock.close()
            await self.sock.wait_closed()
            raise

    async def wait(self) -> None:
        await self.running.wait()

    async def _tcp_recv(
        self, sock: asyncio.StreamReader, length: int, addr: None = None
    ):
        data = await sock.readexactly(length)
        return data

    async def _tcp_send(
        self, sock: asyncio.StreamWriter, data: bytes, addr: None = None
    ):
        sock.write(data)
        await sock.drain()

    async def tcp_recv(self, sock):
        try:
            length = await self._tcp_recv(sock, 4)
            length = struct.unpack(">I", length)[0]

            data = lz4.frame.decompress(await self._tcp_recv(sock, length))

            return data
        except:
            return bytes([])

    async def tcp_send(self, sock, data):
        data = lz4.frame.compress(data)

        length = len(data)
        length = struct.pack(">I", length)

        await self._tcp_send(sock, length)
        await self._tcp_send(sock, data)

    async def tcp_broadcast(self, sockets: list[str], data):
        tasks = []
        for socket in sockets.copy():
            tasks.append(self.tcp_send(self.servers[socket].socket, data))

        await asyncio.gather(*tasks, return_exceptions=True)

    async def tcp_handler(self, r: asyncio.StreamReader, w: asyncio.StreamWriter):
        async def _rcv():
            return await self.tcp_recv(r)

        async def _snd(data: bytes):
            return await self.tcp_send(w, data)

        await self.handler(_rcv, _snd, r, w)

    async def handler(
        self,
        r: Callable[[], bytes],
        w: Callable[[bytes, None], None],
        reader,
        writer: asyncio.StreamWriter,
    ) -> None:
        CREDENTIALS = None

        await w(bytes([Datatypes.REQUEST_AUTH.value]))

        try:
            while True:
                data = await r()

                if len(data) == 0:
                    writer.close()
                    await writer.wait_closed()
                    break

                data, datatype = data[1:], data[0]

                try:
                    match Datatypes(datatype):
                        case Datatypes.SEND_AUTH:
                            CREDENTIALS = await self._handle_send_auth(
                                data, CREDENTIALS, w, writer
                            )

                        case Datatypes.SEND_UDP_AUTH:
                            await self._check(CREDENTIALS, "SEND_UDP_AUTH")
                            await self._handle_send_udp_auth(data, CREDENTIALS, w)

                        case Datatypes.GET_UDP_AUTH:
                            await self._check(CREDENTIALS, "GET_UDP_AUTH")
                            await self._handle_get_udp_auth(data, CREDENTIALS, w)

                        case Datatypes.GET:
                            await self._check(CREDENTIALS, "GET")
                            await self._handle_get(data, CREDENTIALS, w)

                        case Datatypes.POST:
                            await self._check(CREDENTIALS, str(data) + " | POST")
                            await self._handle_post(data, CREDENTIALS, w)

                        case Datatypes.SUBSCRIBE:
                            await self._check(CREDENTIALS, "SUBSCRIBE")
                            await self._handle_subscribe(data, CREDENTIALS, w)

                        case Datatypes.ANON:
                            await self._check(CREDENTIALS, "ANON")
                            await self._handle_anon(data, CREDENTIALS, w)
                            
                        case Datatypes.CREATE_TOPIC:
                            await self._check(CREDENTIALS, "CREATE_TOPIC")
                            await self._handle_create_topic(data, CREDENTIALS, w)

                        # case Datatypes.ROSSTAT:
                        #     await self._check(CREDENTIALS, "ROSSTAT")
                        #     await self._handle_rosstat(w)

                        case Datatypes.ERROR:
                            await self._check(CREDENTIALS, "ERROR")
                            await self._handle_error(data)

                        case _:
                            raise Exception

                except Exception as e:
                    logging.error("\n".join(traceback.format_exception(e)))
                    await self._error(w, Errortypes.METHOD_NOT_FOUND)

        except Exception as e:
            logging.error(e)
            logging.error(f"Line: {e.__traceback__.tb_lineno}")

        finally:
            logging.debug(f"Cleaning: {CREDENTIALS}")
            await self._cleanup(CREDENTIALS)

    async def _cleanup(self, CREDENTIALS):
        if CREDENTIALS in self.servers:
            # unsubscribe from all topics
            for server in self.servers.values():
                for field in server.fields.values():
                    try:
                        field.subscribers.discard(CREDENTIALS)
                    except:
                        pass

            # set client socket to None
            self.servers[CREDENTIALS].socket = None

    async def _check(self, CREDENTIALS: bytes, additional: str | None = None):
        if CREDENTIALS is None:
            raise ConnectionError(
                f"node hasn`t sent valid credentials {('(' + str(additional) + ')') if additional is not None else ''}"
            )

    async def _error(self, w, error: Errortypes, data: bytes = bytes([])):
        await w(bytes([Datatypes.ERROR.value, error.value, *data]))

    async def _handle_error(self, data):
        if len(data) >= 1:
            try:
                logging.warning(Errortypes(data[0]))

            except:
                logging.warning(f"unknown error: {hex(data[0])}")

        else:
            logging.warning(f"unknown error {data}")

    async def _handle_rosstat(self, w):
        tosend = {}
        for x in self.servers.keys():
            v = self.servers[x]
            tosend[x] = v.to_json()

        data = json.dumps(tosend).encode()

        await w(bytes([Datatypes.ROSSTAT.value, len(data), *data]))

    async def _handle_anon(self, data, CREDENTIALS, w):
        name_length = data[0]
        field_length = data[1]

        data_start = 2 + name_length + field_length

        raw_node_name = data[2 : 2 + name_length]
        raw_field_name = data[2 + name_length : 2 + name_length + field_length]

        logging.debug(f"{CREDENTIALS} sent anon to {raw_node_name}/{raw_field_name}")

        if (
            raw_node_name not in self.servers
            or self.servers[raw_node_name].socket is None
        ):
            logging.error(
                f"Failed to send ANON to {raw_field_name}: node {raw_node_name} is not connected ({raw_node_name in self.servers})"
            )
            return await self._error(w, Errortypes.INVALID_ANON_CREDENTIALS)

        await self.tcp_send(
            self.servers[raw_node_name].socket,
            bytes(
                [
                    Datatypes.SEND_ANON.value,
                    len(CREDENTIALS),
                    len(raw_field_name),
                    *CREDENTIALS,
                    *raw_field_name,
                    *data[data_start:],  # additional info
                ]
            ),
        )

    async def _handle_subscribe(self, data, CREDENTIALS, w):
        name_length = data[0]
        field_length = data[1]

        raw_node_name = data[2 : 2 + name_length]
        raw_field_name = data[2 + name_length : 2 + name_length + field_length]

        logging.debug(f"{CREDENTIALS} subscribed to {raw_node_name}/{raw_field_name}")

        if raw_node_name not in self.servers:
            self.servers[raw_node_name] = Connection(raw_node_name, {}, None, None)

        if raw_field_name not in self.servers[raw_node_name].fields:
            self.servers[raw_node_name].fields[raw_field_name] = Field(
                name=raw_field_name,
                data=None,
                subscribers=[CREDENTIALS],
            )
        else:
            self.servers[raw_node_name].fields[raw_field_name].subscribers.add(
                CREDENTIALS
            )

    async def _handle_post(self, data, CREDENTIALS, w):
        field_length = data[0]

        data_start = 1 + field_length

        raw_field_name = data[1:data_start]

        logging.debug(f"{CREDENTIALS} posted to {raw_field_name}")

        if raw_field_name not in self.servers[CREDENTIALS].fields:
            logging.debug(f"{CREDENTIALS} created {raw_field_name}")
            
            self.servers[CREDENTIALS].fields[raw_field_name] = Field(
                name=raw_field_name, data=data[data_start:], subscribers=[]
            )

        else:
            self.servers[CREDENTIALS].fields[raw_field_name].data = data[data_start:]

        await self.tcp_broadcast(
            list(self.servers[CREDENTIALS].fields[raw_field_name].subscribers),
            bytes(
                [
                    Datatypes.SEND_GET.value,
                    len(CREDENTIALS),
                    len(raw_field_name),
                    *CREDENTIALS,
                    *raw_field_name,
                    *self.servers[CREDENTIALS].fields[raw_field_name].data,
                ]
            ),
        )

        await w(bytes([Datatypes.SEND_POST.value, Status.OK.value]))

    async def _handle_create_topic(self, data, CREDENTIALS, w):
        field_length = data[0]
        raw_field_name = data[1:]
        
        logging.debug(f"{CREDENTIALS} created {raw_field_name}")
        
        if raw_field_name not in self.servers[CREDENTIALS].fields:
            self.servers[CREDENTIALS].fields[raw_field_name] = Field(
                name=raw_field_name, data=b"", subscribers=[]
            )
        
        else:
            # TODO: send error
            logging.debug(f"topic {raw_field_name} already exists")
            

    async def _handle_get(self, data, CREDENTIALS, w):
        name_length = data[0]
        field_length = data[1]

        raw_node_name = data[2 : 2 + name_length]
        raw_field_name = data[2 + name_length : 2 + name_length + field_length]

        if (
            raw_node_name not in self.servers
            or raw_field_name not in self.servers[raw_node_name].fields
        ):
            return await self._error(w, Errortypes.INVALID_CREDENTIALS)

        send = self.servers[raw_node_name].fields[raw_field_name].data
        send = send if send else bytes([])
        await w(
            bytes(
                [
                    Datatypes.SEND_GET.value,
                    len(raw_node_name),
                    len(raw_field_name),
                    *raw_node_name,
                    *raw_field_name,
                    *send,
                ]
            )
        )

    async def _handle_get_udp_auth(self, data, CREDENTIALS, w):
        if (
            data not in self.servers or self.servers[data].udp_addr is None
        ):  # data = raw_node_name
            return await self._error(w, Errortypes.INVALID_GET_UDP_CREDENTIALS, data)

        ip, port = self.servers[data].udp_addr  # data = raw_node_name

        await w(
            bytes(
                [
                    Datatypes.SEND_UDP_AUTH.value,
                    len(data),
                    *data,
                    *ip.encode(),
                    *struct.pack(">H", port),
                ]
            )
        )

    async def _handle_send_udp_auth(self, data, CREDENTIALS, w):
        ip = data[:-2].decode()
        port = struct.unpack(">H", data[-2:])[0]

        self.servers[CREDENTIALS].udp_addr = (ip, port)

    async def _handle_send_auth(self, data, CREDENTIALS, w, writer):
        CREDENTIALS = data[1:]

        if CREDENTIALS in self.servers and self.servers[CREDENTIALS].socket is not None:
            return await self._error(w, Errortypes.INVALID_CREDENTIALS)

        elif CREDENTIALS in self.servers:
            self.servers[CREDENTIALS].socket = writer
            self.servers[CREDENTIALS].udp_addr = None

        else:
            self.servers[CREDENTIALS] = Connection(
                name=CREDENTIALS,
                fields={},
                socket=writer,
                udp_addr=None,
            )

        return CREDENTIALS


# TODO:  Implement a maximum buffer size per address with overflow handling (drop oldest or newest). Add periodic cleanup of stale buffer entries
class _ClientRecvProtocol(asyncio.DatagramProtocol):
    def __init__(self, root: "AsyncDistributedClient"):
        super().__init__()
        self.root: "AsyncDistributedClient" = root

    def connection_made(self, transport):
        self.transport = transport

    def datagram_received(self, data: bytes, addr: AddrLike):
        if addr in self.root.udp_buffers:
            self.root.udp_buffers[addr] += data

        else:
            self.root.udp_buffers[addr] = data


class UDPConnection:
    def __init__(self, ip: str, port: int, name: str):
        self.ip = ip
        self.port = port
        self.name = name

        self.has_connection = False
        self.has_tried_to_connect = False


class AsyncDistributedClient:
    def __init__(self, ip, port, name):
        self.ip = ip
        self.port = port
        self.name = name

        self.received = {}
        self.handlers = {}
        self.anon_handlers = {}

        self.udp_buffers: dict[AddrLike, bytes] = {}
        self.udp_servers: dict[str, UDPConnection] = {}

        self.r: asyncio.StreamReader | None = None
        self.w: asyncio.StreamWriter | None = None

        self.transport: asyncio.DatagramTransport | None = None

        self._is_running = asyncio.Event()
        self._is_sended_credentials = asyncio.Event()

        self._tcp_request_queue: Queue[bytes] = Queue(100)

    async def subscribe(self, node: str, field: str, handler: Callable | None) -> None:
        await self.send(
            bytes(
                [
                    Datatypes.SUBSCRIBE.value,
                    len(node),
                    len(field),
                    *node.encode(),
                    *field.encode(),
                ]
            )
        )

        if handler is not None:
            if node not in self.handlers:
                self.handlers[node] = {}

            self.handlers[node][field] = handler

    async def unsubscribe(self, node: str, field: str) -> None:
        await self.send(
            bytes(
                [
                    Datatypes.UNSUBSCRIBE.value,
                    len(node),
                    len(field),
                    *node.encode(),
                    *field.encode(),
                ]
            )
        )

    async def post(self, field: str, data: bytes) -> None:
        await self.send(
            bytes(
                [
                    Datatypes.POST.value,
                    len(field),
                    *field.encode(),
                    *data,
                ]
            )
        )

    async def anon(
        self, node: str, field: str, data: bytes, force_to_tcp: bool = False
    ) -> None:
        if (
            not force_to_tcp
            and node in self.udp_servers
            and self.udp_servers[node].has_connection
        ):
            raw_name = self.name.encode()
            raw_field = field.encode()

            await self.send_udp(
                bytes(
                    [
                        DistributedDatatypes.ANON.value,
                        len(raw_name),
                        len(raw_field),
                        *raw_name,
                        *raw_field,
                        *data,
                    ]
                ),
                (self.udp_servers[node].ip, self.udp_servers[node].port),
            )

        elif (
            force_to_tcp
            or node in self.udp_servers
            and self.udp_servers[node].has_tried_to_connect
        ):
            await self.send(
                bytes(
                    [
                        Datatypes.ANON.value,
                        len(node),
                        len(field),
                        *node.encode(),
                        *field.encode(),
                        *data,
                    ]
                )
            )

        elif node not in self.udp_servers:
            await self.send(bytes([Datatypes.GET_UDP_AUTH.value, *node.encode()]))

            await self.send(
                bytes(
                    [
                        Datatypes.ANON.value,
                        len(node),
                        len(field),
                        *node.encode(),
                        *field.encode(),
                        *data,
                    ]
                )
            )

        else:
            await self.send_udp(
                bytes(
                    [
                        DistributedDatatypes.PING.value,
                    ]
                ),
                (self.udp_servers[node].ip, self.udp_servers[node].port),
            )

            # TODO: Use asyncio.Event or asyncio.wait_for() with a proper timeout. Decouple the ping-pong handshake from the message send path
            counter = 0
            self.udp_servers[node].has_tried_to_connect = True
            while not self.udp_servers[node].has_connection and counter < 100:
                counter += 1
                await asyncio.sleep(0.05)

            if self.udp_servers[node].has_connection:
                raw_name = self.name.encode()
                raw_field = field.encode()

                await self.send_udp(
                    bytes(
                        [
                            DistributedDatatypes.ANON.value,
                            len(raw_name),
                            len(raw_field),
                            *raw_name,
                            *raw_field,
                            *data,
                        ]
                    ),
                    (self.udp_servers[node].ip, self.udp_servers[node].port),
                )

            else:
                await self.send(
                    bytes(
                        [
                            Datatypes.ANON.value,
                            len(self.name),
                            len(field),
                            *node.encode(),
                            *field.encode(),
                            *data,
                        ]
                    )
                )

    async def create_topic(self, field: str) -> None:
        await self.send(
            bytes(
                [
                    Datatypes.CREATE_TOPIC.value,
                    len(field),
                    *field.encode()
                ]
            )
        )

    # async def rosstat(self) -> None:
    #     await self.send(
    #         bytes(
    #             [
    #                 Datatypes.ROSSTAT.value,
    #             ]
    #         )
    #     )

    async def _recv(self, length: int) -> bytes:
        return await self.r.readexactly(length)

    async def _send(self, data) -> None:
        self.w.write(data)
        await self.w.drain()

    async def recv(self):
        try:
            length = await self._recv(4)
            length = struct.unpack(">I", length)[0]

            return lz4.frame.decompress(await self._recv(length))
            # return zlib.decompress(await self._recv(length))

        except Exception as e:
            logging.exception(e)
            return bytes([])

    async def send(self, data):
        # data = zlib.compress(data)
        data = lz4.frame.compress(data)

        length = len(data)
        length = struct.pack(">I", length)

        ## why?
        # if data[0] == 0x01:
        #     raise Exception("")

        await self._send(length)
        await self._send(data)

    async def send_udp(self, data: bytes, addr: AddrLike):
        self.transport.sendto(struct.pack(">I", len(data)) + data, addr)

    # TODO: add an Queue to properly handle situations when requests are sending too fast
    async def _tcp_mainloop(self):
        while self._is_running.is_set():
            data = await self.recv()

            if len(data) <= 0:
                await asyncio.sleep(0.05)
                continue

            await self._tcp_request_queue.put(data)

    async def _tcp_handler(self):
        while self._is_running.is_set():
            data = await self._tcp_request_queue.get()
            data, datatype = data[1:], data[0]

            try:
                match Datatypes(datatype):
                    case Datatypes.REQUEST_AUTH:
                        logging.debug("REQUEST_AUTH")

                        CREDENTIALS = self.name.encode()

                        await self.send(
                            bytes(
                                [
                                    Datatypes.SEND_AUTH.value,
                                    len(CREDENTIALS),
                                    *CREDENTIALS,
                                ]
                            )
                        )

                        ip, port = self.transport.get_extra_info("sockname")[:2]

                        await self.send(
                            bytes(
                                [
                                    Datatypes.SEND_UDP_AUTH.value,
                                    *ip.encode(),
                                    *struct.pack(">H", int(port)),
                                ]
                            )
                        )

                        self._is_sended_credentials.set()

                    case Datatypes.SEND_UDP_AUTH:
                        logging.debug("SEND_UDP_AUTH")

                        node_name_len = data[0]
                        node_name = data[1 : 1 + node_name_len].decode()

                        if node_name in self.udp_servers:
                            continue

                        ip = data[1 + node_name_len : -2].decode()
                        port = struct.unpack(">H", data[-2:])[0]

                        self.udp_servers[node_name] = UDPConnection(
                            ip,
                            port,
                            node_name,
                        )
                        self.udp_buffers[(ip, port)] = b""

                    case Datatypes.SEND_GET:
                        logging.debug("SEND_GET")

                        name_length = data[0]
                        field_length = data[1]

                        data_start = 2 + name_length + field_length

                        node_name = data[2 : 2 + name_length].decode()
                        field_name = data[
                            2 + name_length : 2 + name_length + field_length
                        ].decode()

                        if node_name not in self.received:
                            self.received[node_name] = {}

                        self.received[node_name][field_name] = data[data_start:]
                        if (
                            node_name in self.handlers
                            and field_name in self.handlers[node_name]
                        ):
                            result = await self.handlers[node_name][field_name](
                                data[data_start:]
                            )
                            if result is not None:
                                logging.debug(
                                    f"[{self.name}] {node_name}:{field_name}: {result}"
                                )

                    case Datatypes.SEND_POST:
                        logging.debug("SEND_POST")

                    case Datatypes.ERROR:
                        logging.debug("ERROR")
                        logging.debug(data)

                        match Errortypes(data[0]):
                            case Errortypes.NODE_EXISTS:
                                logging.error("Node name already exists")
                                break

                            case Errortypes.INVALID_CREDENTIALS:
                                logging.error("Sended invalid credentials")
                                break

                            case Errortypes.METHOD_NOT_FOUND:
                                logging.error("Requested method not found")

                            case Errortypes.INVALID_SUBSCRIBE:
                                logging.error("Sended invalid subscribe credentials")

                            case Errortypes.INVALID_ANON_CREDENTIALS:
                                logging.error("Sended invalid ANON credentials")

                            case Errortypes.INVALID_GET_UDP_CREDENTIALS:
                                logging.error("Sended invalid GET_UDP credentials")

                                name = data[2:].decode()

                                if name in self.udp_servers:
                                    self.udp_servers[name].has_connection = False
                                    self.udp_servers[name].has_tried_to_connect = True

                                else:
                                    self.udp_servers[name] = UDPConnection("", -1, name)
                                    self.udp_servers[name].has_connection = False
                                    self.udp_servers[name].has_tried_to_connect = True

                            case _:
                                logging.error("unknown error")

                    case Datatypes.SEND_ANON:
                        logging.debug("SEND_ANON")

                        name_length = data[0]
                        field_length = data[1]

                        data_start = 2 + name_length + field_length

                        node_name = data[2 : 2 + name_length].decode()
                        field_name = data[
                            2 + name_length : 2 + name_length + field_length
                        ].decode()

                        if field_name in self.anon_handlers:
                            result = await self.anon_handlers[field_name](
                                data[data_start:], node_name
                            )
                            if result is not None:
                                logging.debug(
                                    f"[{self.name}] anon:{field_name}: {result}"
                                )

                    case Datatypes.ROSSTAT:
                        self.on_rosstat(json.loads(data.decode()))

                    case _:
                        raise Exception

            except Exception as e:
                logging.exception(e)
                await self.send(
                    bytes([Datatypes.ERROR.value, Errortypes.METHOD_NOT_FOUND.value])
                )

    # TODO: add an Queue to properly handle situations when requests are sending too fast
    async def _udp_mainloop(self):
        while self._is_running.is_set():
            tasks = []
            addrs = []
            for buf in self.udp_buffers.keys():
                if len(self.udp_buffers[buf]) > 0:
                    addrs.append(buf)
                    tasks.append(self._udp_mainloop_handler(self.udp_buffers[buf], buf))

            results = await asyncio.gather(*tasks)

            for res, addr in zip(results, addrs):
                self.udp_buffers[addr] = self.udp_buffers[addr][res:]

            await asyncio.sleep(0.01)

    async def _udp_mainloop_handler(self, data: bytes, addr: AddrLike) -> int:
        length = struct.unpack(">I", data[:4])[0]

        data = data[4 : 4 + length]

        datatype, data = data[0], data[1:]

        match DistributedDatatypes(datatype):
            case DistributedDatatypes.PING:
                await self.send_udp(
                    bytes(
                        [
                            DistributedDatatypes.PONG.value,
                        ]
                    ),
                    addr,
                )

            case DistributedDatatypes.PONG:
                for server in self.udp_servers.values():
                    if server.ip == addr[0] and server.port == addr[1]:
                        server.has_connection = True
                        server.has_tried_to_connect = True
                        break

            case DistributedDatatypes.ANON:
                name_length = data[0]
                field_length = data[1]

                data_start = 2 + name_length + field_length

                node_name = data[2 : 2 + name_length].decode()
                field_name = data[
                    2 + name_length : 2 + name_length + field_length
                ].decode()

                if field_name in self.anon_handlers:
                    await self.anon_handlers[field_name](data[data_start:], node_name)

        return 4 + length

    async def mainloop(self):
        r, w = await asyncio.open_connection(self.ip, self.port, family=socket.AF_INET)

        self.r = r
        self.w = w

        transport, protocol = await asyncio.get_event_loop().create_datagram_endpoint(
            lambda: _ClientRecvProtocol(self),
            local_addr=("localhost", random.randint(12000, 65535)),
            family=socket.AF_INET,
        )

        self.transport = transport

        self._is_running.set()

        try:
            tcp_task = asyncio.create_task(self._tcp_mainloop())
            tcp_queue_task = asyncio.create_task(self._tcp_handler())
            udp_task = asyncio.create_task(self._udp_mainloop())

            done, pending = await asyncio.wait(
                [tcp_task, udp_task, tcp_queue_task],
                return_when=asyncio.FIRST_COMPLETED,
            )

            for task in pending:
                task.cancel()

            await asyncio.gather(
                *pending,
                return_exceptions=True,
            )

        except asyncio.CancelledError:
            self._is_running.clear()

            for task in [tcp_task, udp_task]:
                if not task.done():
                    task.cancel()

            await asyncio.gather(tcp_task, udp_task, return_exceptions=True)
            raise

        finally:
            if self.w:
                self.w.close()
                await self.w.wait_closed()
