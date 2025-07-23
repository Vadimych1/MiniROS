import socket
import struct
import logging
import zlib
import threading
from enum import Enum
from typing import Callable
import json
import time
import asyncio
import random
import traceback

AddrLike = str | tuple[str, int]


class Datatypes(Enum):
    ERROR = 0x00
    
    POST = 0x01
    SEND_POST = 0x02
    
    GET = 0x03
    SEND_GET = 0x04

    SUBSCRIBE = 0x05
    UNSUBSCRIBE = 0x06

    ANON = 0x07
    SEND_ANON = 0x08

    ROSSTAT = 0xfd

    GET_UDP_AUTH = 0xfc
    SEND_UDP_AUTH = 0xfd
    REQUEST_AUTH = 0xfe
    SEND_AUTH = 0xff


class Errortypes(Enum):
    NODE_EXISTS = 0x00
    METHOD_NOT_FOUND = 0x01
    INVALID_CREDENTIALS = 0x02
    INVALID_SUBSCRIBE = 0x03
    INVALID_ANON_CREDENTIALS = 0x04
    INVALID_GET_UDP_CREDENTIALS = 0x05


class DistributedDatatypes(Enum):
    PING = 0x00
    PONG = 0x01

    ANON = 0x02


class Status(Enum):
    OK = 0x00
    ERROR = 0x01


def new_sock(use_udp: bool = False) -> socket.socket:
    """
    Initializes new fast socket
    :param 
    """
    
    sock = None
    if "AF_UNIX" in socket.__dict__ and False: # TODO: fix unix sockets
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM if use_udp else socket.SOCK_STREAM)

    else:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM if use_udp else socket.SOCK_STREAM)

    # sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1) if not use_udp else ...
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 1024 * 1024 * 32)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 1024 * 1024 * 32)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    # sock.setblocking(False)

    return sock


class Field:
    __slots__ = ("name", "data", "subscribers")
    def __init__(self, name: bytes, data: bytes, subscribers: list[str]):
        self.data = data
        self.subscribers = subscribers
        self.name = name

    def to_json(self):
        return {
            "name": self.name.decode(),
            "subscribers": list(map(bytes.decode, self.subscribers))
        }

class Connection:
    __slots__ = ("name", "fields", "socket", "udp_addr")
    def __init__(self, name: bytes, fields: dict[str, Field], socket: "socket.socket", udp_addr: AddrLike):
        self.name = name
        self.fields = fields
        self.socket = socket
        self.udp_addr = udp_addr

    def to_json(self):
        return {
            "name": self.name.decode(),
            "fields": list(map(lambda x: x.to_json(), self.fields.values())),
        }

class SockServer:
    """
    Socket server base class
    Implements basic methods for interacting with clients
    """

    def __init__(self, ip: str, port: int):
        self.ip = ip
        self.port = port
        self.servers: dict[str, Connection] = {}

        self.sending = False # fix for byte-mismatch


    def send(self, sock: socket.socket, data: bytes, addr: None | AddrLike) -> None:
        data = zlib.compress(data)
        length = len(data)
        length = struct.pack(">I", length)

        while self.sending:
            time.sleep(0.01)
        
        self.sending = True

        self._send(sock, length, addr)
        self._send(sock, data, addr)
        
        self.sending = False


    def recv(self, sock: socket.socket, addr: None | AddrLike) -> bytes:
        try:
            length = self._recv(sock, 4, addr)
            length = struct.unpack(">I", length)[0]
            logging.info(f"WAITING FOR {length}")
            return zlib.decompress(self._recv(sock, length, addr))        
        except:
            return bytes([])
            

    def _recv(self, sock, length, addr):
        ...


    def _send(self, sock, data, addr):
        ...


    def handler(self, conn: socket.socket, addr: None | AddrLike) -> None:
        CREDENTIALS = None

        self.send(conn, bytes([Datatypes.REQUEST_AUTH.value]), addr)
        
        try:
            while True:
                data = self.recv(conn, addr)
                
                if len(data) <= 0:
                    break # TODO: get reason of data len 0
                
                data, datatype = data[1:], data[0]

                try:
                    match Datatypes(datatype):
                        case Datatypes.SEND_AUTH:
                            logging.debug("GOT SEND_AUTH")

                            CREDENTIALS = data[1:].decode()

                            if CREDENTIALS in self.servers:
                                self.send(conn, bytes([Datatypes.ERROR.value, Errortypes.INVALID_CREDENTIALS.value]), addr)
                                continue

                            self.servers[CREDENTIALS] = Connection(
                                name=CREDENTIALS,
                                fields={},
                                socket=conn
                            )

                        case Datatypes.GET:
                            logging.debug("GOT GET")

                            raw_node_name = data[0:3]
                            raw_field_name = data[3:6]
                            node_name = raw_node_name.decode()
                            field_name = raw_field_name.decode()

                            if node_name not in self.servers or field_name not in self.servers[node_name].fields:
                                self.send(conn, bytes([
                                    Datatypes.ERROR.value,
                                    Errortypes.INVALID_CREDENTIALS.value
                                ]), addr)
                                continue

                            send = self.servers[node_name].fields[field_name].data
                            send = send if send else bytes([])
                            self.send(conn, bytes([
                                Datatypes.SEND_GET.value,
                                len(raw_node_name),
                                len(raw_field_name),
                                *raw_node_name,
                                *raw_field_name,
                                *send,
                            ]), addr)

                        case Datatypes.POST:
                            logging.debug("GOT POST")

                            field_length = data[0]

                            data_start = 1+field_length

                            raw_field_name = data[1:data_start]
                            field_name = raw_field_name.decode()

                            if field_name not in self.servers[CREDENTIALS].fields:
                                self.servers[CREDENTIALS].fields[field_name] = Field(
                                    name = field_name,
                                    data=data[data_start:],
                                    subscribers=[]
                                )
                                
                            else:
                                self.servers[CREDENTIALS].fields[field_name].data = data[data_start:]
                            
                            for subscriber in self.servers[CREDENTIALS].fields[field_name].subscribers:
                                self.send(self.servers[subscriber].socket, bytes([
                                    Datatypes.SEND_GET.value,
                                    len(CREDENTIALS),
                                    len(raw_field_name),
                                    *CREDENTIALS.encode(),
                                    *raw_field_name,
                                    *self.servers[CREDENTIALS].fields[field_name].data,
                                ]), addr)
                            

                            self.send(conn, bytes([
                                Datatypes.SEND_POST.value,
                                Status.OK.value
                            ]), addr)

                        case Datatypes.SUBSCRIBE:
                            logging.debug("GOT SUBSCRIBE")

                            name_length = data[0]
                            field_length = data[1]

                            data_start = 2+name_length+field_length

                            raw_node_name = data[2:2+name_length]
                            raw_field_name = data[2+name_length:2+name_length+field_length]

                            node_name = raw_node_name.decode()
                            field_name = raw_field_name.decode()

                            if node_name not in self.servers:
                                self.send(conn, bytes([
                                    Datatypes.ERROR.value,
                                    Errortypes.INVALID_SUBSCRIBE.value
                                ]), addr)
                                continue

                            if field_name not in self.servers[node_name].fields:
                                self.servers[node_name].fields[field_name] = Field(
                                    field_name, # TODO: fix type mismatch (field_name is str, required bytes)
                                    data=None,
                                    subscribers=[CREDENTIALS],
                                )
                            else:
                                self.servers[node_name].fields[field_name].subscribers.append(CREDENTIALS)

                        case Datatypes.ANON:
                            logging.debug("GOT ANON")

                            name_length = data[0]
                            field_length = data[1]

                            data_start = 2+name_length+field_length

                            raw_node_name = data[2:2+name_length]
                            raw_field_name = data[2+name_length:2+name_length+field_length]

                            node_name = raw_node_name.decode()
                            field_name = raw_field_name.decode()

                            if node_name not in self.servers:
                                self.send(conn, bytes([
                                    Datatypes.ERROR.value,
                                    Errortypes.INVALID_ANON_CREDENTIALS.value
                                ]), addr)
                                continue

                            self.send(self.servers[node_name].socket, bytes([
                                Datatypes.SEND_ANON.value,
                                len(CREDENTIALS),
                                len(raw_field_name),
                                *CREDENTIALS.encode(),
                                *raw_field_name,
                                *data[data_start:], # additional info
                            ]), addr)

                        case Datatypes.ROSSTAT:
                            logging.debug("GOT ROSSTAT")

                            # tosend = {}
                            # for x in self.servers.keys():
                            #     v = self.servers[x]

                            #     for fld in v.fields.keys():
                            #         del v.fields[fld].data

                            #     del v.socket
                            #     tosend[x] = v

                            # self.send(conn, bytes([
                            #     Datatypes.ROSSTAT.value,
                            #     *json.dumps(tosend).encode()
                            # ]), addr)

                            # TODO: fix rosstat (add json encoder to Field and Connection classes)

                        case _:
                            raise Exception
                
                except Exception as e:
                    logging.error("\n".join(traceback.format_exception(e)))
                    self.send(conn, bytes([Datatypes.ERROR.value, Errortypes.METHOD_NOT_FOUND.value]), addr)

        except Exception as e:
            logging.error("\n".join(traceback.format_exception(e)))
        
        finally:
            if CREDENTIALS in self.servers:
                del self.servers[CREDENTIALS]

class SockClient:
    def __init__(self, ip: str, port: int, name: str):
        self.ip = ip
        self.port = port
        self.name = name

        self.received = {}
        self.handlers = {}
        self.anon_handlers = {}

        self.sending = False # fix for byte-mismatch

        self.on_rosstat = lambda *val: ...

    def send(self, data: bytes) -> None:
        data = zlib.compress(data)
        length = len(data)
        length = struct.pack(">I", length)

        while self.sending:
            time.sleep(0.005)

        self.sending = True

        self._send(length)
        self._send(data)
        
        self.sending = False

    def recv(self) -> bytes:
        try:
            length = self._recv(4)
            length = struct.unpack(">I", length)[0]
            return zlib.decompress(self._recv(length))
        except:
            return bytes([])

    def _recv(self, length) -> bytes:
        ...

    def _send(self, data) -> bytes:
        ...
    
    def subscribe(self, node: str, field: str, handler: Callable | None) -> None:
        self.send(bytes([
            Datatypes.SUBSCRIBE.value,
            len(node),
            len(field),
            *node.encode(),
            *field.encode(),
        ]))

        if handler is not None:
            if node not in self.handlers:
                self.handlers[node] = {}

            self.handlers[node][field] = handler

            logging.debug(f"ADDED HANDLER {node}:{field}")

    def unsubscribe(self, node: str, field: str) -> None:
        self.send(bytes([
            Datatypes.UNSUBSCRIBE.value,
            len(node),
            len(field),
            *node.encode(),
            *field.encode(),
        ]))

    def post(self, field: str, data: bytes) -> None:
        self.send(bytes([
            Datatypes.POST.value,
            len(field),
            *field.encode(),
            *data,
        ]))

    def anon(self, node: str, field: str, data: bytes) -> None:
        self.send(bytes([
            Datatypes.ANON.value,
            len(node),
            len(field),
            *node.encode(),
            *field.encode(),
            *data
        ]))

    def rosstat(self) -> None:
        self.send(bytes([
            Datatypes.ROSSTAT.value,
        ]))

    def mainloop(self):
        while True:
            data = self.recv()
            data, datatype = data[1:], data[0]

            try:
                match Datatypes(datatype):
                    case Datatypes.REQUEST_AUTH:
                        logging.debug("GOT REQUEST_AUTH")

                        CREDENTIALS = self.name.encode()

                        self.send(bytes([
                            Datatypes.SEND_AUTH.value,
                            len(CREDENTIALS),
                            *CREDENTIALS
                        ]))

                    case Datatypes.SEND_GET:
                        logging.debug("GOT SEND_GET")
                        
                        name_length = data[0]
                        field_length = data[1]

                        data_start = 2+name_length+field_length

                        node_name = data[2:2+name_length].decode()
                        field_name = data[2+name_length:2+name_length+field_length].decode()

                        if node_name not in self.received:
                            self.received[node_name] = {}

                        self.received[node_name][field_name] = data[data_start:]
                        if node_name in self.handlers and field_name in self.handlers[node_name]:
                            self.handlers[node_name][field_name](data[data_start:])

                    case Datatypes.SEND_POST:
                        logging.debug("GOT SEND_POST")

                    case Datatypes.ERROR:
                        logging.debug("GOT ERROR")
                        logging.debug(data)

                        match data[0]:
                            case Errortypes.NODE_EXISTS.value:
                                logging.error("Node name already exists")
                                break

                            case Errortypes.INVALID_CREDENTIALS.value:
                                logging.error("Sended invalid credentials")
                                break

                            case Errortypes.METHOD_NOT_FOUND.value:
                                logging.error("Requested method not found")

                            case Errortypes.INVALID_SUBSCRIBE.value:
                                logging.error("Sended invalid subscribe credentials")

                            case _:
                                logging.error("Got unknown error")

                    case Datatypes.SEND_ANON:
                        logging.debug("GOT SEND_ANON")

                        name_length = data[0]
                        field_length = data[1]

                        data_start = 2+name_length+field_length

                        node_name = data[2:2+name_length].decode()
                        field_name = data[2+name_length:2+name_length+field_length].decode()

                        self.anon_handlers[field_name](data[data_start:], node_name)

                    case Datatypes.ROSSTAT:
                        self.on_rosstat(json.loads(data.decode()))

                    case _:
                        raise Exception

            except Exception as e:
                self.send(bytes([Datatypes.ERROR.value, Errortypes.METHOD_NOT_FOUND.value]))        


class TCPSockServer(SockServer):
    def __init__(self, ip: str, port: int):
        self.sock = new_sock(False)
        self.sock.bind((ip.encode(), port))
        super().__init__(ip, port)

    def run(self) -> None:
        self.sock.listen()
        while True:
            conn, addr = self.sock.accept()
            threading.Thread(target=self.handler, args=(conn, addr)).start()

    def _recv(self, sock: socket.socket, length, addr):
        return sock.recv(length)
    
    def _send(self, sock: socket.socket, data, addr):
        return sock.send(data)

class TCPSockClient(SockClient):
    def __init__(self, ip: str, port: int, name: str):
        self.sock = new_sock(False)
        self.sock.connect((ip.encode(), port))
        super().__init__(ip, port, name)

    def _recv(self, length):
        return self.sock.recv(length)
    
    def _send(self, data):
        return self.sock.send(data)


class AsyncDistributedServer(SockServer):
    """
    Async TCP server class
     
    Allows adding a "udp_addr" property to each tcp connection which can be requested by other clients.
    
    Requested address can be used on clients to send ANON messages to other clients directly
    """

    def __init__(self, ip: str, port: int):

        self.sock = None
        self.running = False
        
        super().__init__(ip, port)


    async def run(self) -> None:
        self.sock: asyncio.Server = await asyncio.start_server(self.tcp_handler, self.ip, self.port)

        self.running = True
        await self.sock.serve_forever()


    async def wait(self) -> None:
        while not self.running:
            await asyncio.sleep(0.05)


    async def _tcp_recv(self, sock: asyncio.StreamReader, length: int, addr: None = None):
        return await sock.readexactly(length)

    
    async def _tcp_send(self, sock: asyncio.StreamWriter, data: bytes, addr: None = None):
        sock.write(data)
        await sock.drain()


    async def tcp_recv(self, sock):
        try:
            length = await self._tcp_recv(sock, 4)
            length = struct.unpack(">I", length)[0]
            return zlib.decompress(await self._tcp_recv(sock, length))        
        except:
            return bytes([])


    async def tcp_send(self, sock, data):
        data = zlib.compress(data)
        length = len(data)
        length = struct.pack(">I", length)

        while self.sending:
            await asyncio.sleep(0.01)
        
        self.sending = True

        await self._tcp_send(sock, length)
        await self._tcp_send(sock, data)
        
        self.sending = False


    async def tcp_broadcast(self, sockets: list[str], data):
        tasks = []
        for socket in sockets.copy():
            tasks.append(self.tcp_send(self.servers[socket].socket, data))
        await asyncio.gather(*tasks, return_exceptions=False)


    async def tcp_handler(self, r: asyncio.StreamReader, w: asyncio.StreamWriter):
        async def rcv():
            return await self.tcp_recv(r)
        
        async def snd(data: bytes):
            return await self.tcp_send(w, data)

        await self.handler(
            rcv,
            snd,
            r, w
        )


    async def handler(self, r: Callable[[], bytes], w: Callable[[bytes, None], None], reader, writer: asyncio.StreamWriter) -> None:
        CREDENTIALS = None

        await w(bytes([Datatypes.REQUEST_AUTH.value]))
        
        try:
            while True:
                data = await r()

                if len(data) <= 0:
                    writer.close()
                    break

                data, datatype = data[1:], data[0]

                try:
                    match Datatypes(datatype):
                        case Datatypes.SEND_AUTH:
                            CREDENTIALS = await self._handle_send_auth(data, CREDENTIALS, w, writer)

                        case Datatypes.SEND_UDP_AUTH:
                            await self._check(CREDENTIALS)
                            await self._handle_send_udp_auth(data, CREDENTIALS, w)

                        case Datatypes.GET_UDP_AUTH:
                            await self._check(CREDENTIALS)
                            await self._handle_get_udp_auth(data, CREDENTIALS, w)

                        case Datatypes.GET:
                            await self._check(CREDENTIALS)
                            await self._handle_get(data, CREDENTIALS, w)

                        case Datatypes.POST:
                            await self._check(CREDENTIALS)
                            await self._handle_post(data, CREDENTIALS, w)

                        case Datatypes.SUBSCRIBE:
                            await self._check(CREDENTIALS)
                            await self._handle_subscribe(data, CREDENTIALS, w)

                        case Datatypes.ANON:
                            await self._check(CREDENTIALS)
                            await self._handle_anon(data, CREDENTIALS, w)

                        case Datatypes.ROSSTAT:
                            await self._check(CREDENTIALS)
                            await self._handle_rosstat(w)

                        case Datatypes.ERROR:
                            await self._check(CREDENTIALS)
                            await self._handle_error(data)
                            
                        case _:
                            raise Exception
                
                except Exception as e:
                    logging.error("\n".join(traceback.format_exception(e)))
                    await self._error(w, Errortypes.METHOD_NOT_FOUND)

        except Exception as e:
            logging.error(e)
            logging.error(f'Line: {e.__traceback__.tb_lineno}')

        finally:
            await self._cleanup(CREDENTIALS)
                        

    async def _cleanup(self, CREDENTIALS):
        if CREDENTIALS in self.servers:
            # unsubscribe from all topics
            for server in self.servers.values():
                for field in server.fields.values():
                    try:
                        while CREDENTIALS in field.subscribers:
                            field.subscribers.remove(CREDENTIALS)
                    except: pass
                    
            # set client socket to None
            self.servers[CREDENTIALS].socket = None 
                
                    
    async def _check(self, CREDENTIALS):
        if CREDENTIALS is None: 
            raise ConnectionError("node hasn`t sended valid credentials")

    
    async def _error(self, w, error: Errortypes, data: bytes = bytes([])):
        await w(bytes([
            Datatypes.ERROR.value,
            error.value,
            *data
        ]))
                        
                        
    async def _handle_error(self, data):
        if len(data) >= 1:    
            try:
                logging.warning(Errortypes(data[0]))
            
            except:
                logging.warning(f'Got unknown error: {hex(data[0])}')

        else:
            logging.warning(f'Got unknown error {data}')

    async def _handle_rosstat(self, w):
        tosend = {}
        for x in self.servers.keys():
            v = self.servers[x]
            tosend[x] = v.to_json()

        data = json.dumps(tosend).encode()

        await w(bytes([
            Datatypes.ROSSTAT.value,
            len(data),
            *data
        ]))
      
        
    async def _handle_anon(self, data, CREDENTIALS, w):
        name_length = data[0]
        field_length = data[1]

        data_start = 2+name_length+field_length

        raw_node_name = data[2:2+name_length]
        raw_field_name = data[2+name_length:2+name_length+field_length]

        if raw_node_name not in self.servers or self.servers[raw_node_name].socket is None:
            return await self._error(w, Errortypes.INVALID_ANON_CREDENTIALS)

        await self.tcp_send(self.servers[raw_node_name].socket, bytes([
            Datatypes.SEND_ANON.value,
            len(CREDENTIALS),
            len(raw_field_name),
            *CREDENTIALS,
            *raw_field_name,
            *data[data_start:], # additional info
        ]))


    async def _handle_subscribe(self, data, CREDENTIALS, w):
        name_length = data[0]
        field_length = data[1]
        
        raw_node_name = data[2:2+name_length]
        raw_field_name = data[2+name_length:2+name_length+field_length]

        ## old logic: fails when superserver is used (superserver connects before other nodes)
        # if raw_node_name not in self.servers:
        #     return await self._error(w, Errortypes.INVALID_SUBSCRIBE)

        # new logic: creates server and topic if someone wants to subscribe
        if raw_node_name not in self.servers:
            self.servers[raw_node_name] = Connection(
                raw_node_name,
                {},
                None,
                None
            )

        if raw_field_name not in self.servers[raw_node_name].fields:
            self.servers[raw_node_name].fields[raw_field_name] = Field(
                name=raw_field_name,
                data=None,
                subscribers=[CREDENTIALS],
            )
        else:
            self.servers[raw_node_name].fields[raw_field_name].subscribers.append(CREDENTIALS)


    async def _handle_post(self, data, CREDENTIALS, w):
        field_length = data[0]

        data_start = 1+field_length

        raw_field_name = data[1:data_start]

        if raw_field_name not in self.servers[CREDENTIALS].fields:
            self.servers[CREDENTIALS].fields[raw_field_name] = Field(
                name=raw_field_name,
                data=data[data_start:],
                subscribers=[]
            )
            
        else:
            self.servers[CREDENTIALS].fields[raw_field_name].data = data[data_start:]
        
        await self.tcp_broadcast(self.servers[CREDENTIALS].fields[raw_field_name].subscribers, bytes([
            Datatypes.SEND_GET.value,
            len(CREDENTIALS),
            len(raw_field_name),
            *CREDENTIALS,
            *raw_field_name,
            *self.servers[CREDENTIALS].fields[raw_field_name].data,
        ]))

        await w(bytes([
            Datatypes.SEND_POST.value,
            Status.OK.value
        ]))


    async def _handle_get(self, data, CREDENTIALS, w):
        name_length = data[0]
        field_length = data[1]

        raw_node_name = data[2:2+name_length]
        raw_field_name = data[2+name_length:2+name_length+field_length]

        if raw_node_name not in self.servers or raw_field_name not in self.servers[raw_node_name].fields:
            return await self._error(w, Errortypes.INVALID_CREDENTIALS)

        send = self.servers[raw_node_name].fields[raw_field_name].data
        send = send if send else bytes([])
        await w(bytes([
            Datatypes.SEND_GET.value,
            len(raw_node_name),
            len(raw_field_name),
            *raw_node_name,
            *raw_field_name,
            *send,
        ]))


    async def _handle_get_udp_auth(self, data, CREDENTIALS, w):
        if data not in self.servers or self.servers[data].udp_addr is None: # data = raw_node_name
            return await self._error(w, Errortypes.INVALID_GET_UDP_CREDENTIALS, data)

        ip, port = self.servers[data].udp_addr # data = raw_node_name

        await w(bytes([
            Datatypes.SEND_UDP_AUTH.value,
            len(data),
            *data,
            *ip.encode(),
            *struct.pack(">H", port)
        ]))


    async def _handle_send_udp_auth(self, data, CREDENTIALS, w):
        ip = data[:-2].decode()
        port = struct.unpack(">H", data[-2:])[0]

        self.servers[CREDENTIALS].udp_addr = (ip, port)
    
    
    async def _handle_send_auth(self, data, CREDENTIALS, w, writer):
        CREDENTIALS = data[1:]

        ## old logic: fails with superserver behaviour
        # if CREDENTIALS in self.servers:
        #     return await self._error(w, Errortypes.INVALID_CREDENTIALS)

        # return error only if client connections is not None
        if CREDENTIALS in self.servers and self.servers[CREDENTIALS].socket is not None:
            return await self._error(w, Errortypes.INVALID_CREDENTIALS)

        # if client was disconnected, change socket and reset UDP addr
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
    

class _ClientRecvProtocol(asyncio.DatagramProtocol):
    def __init__(self, root):
        super().__init__()
        self.root: "AsyncDistrubutedClient" = root

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

class AsyncDistrubutedClient(SockClient):
    def __init__(self, ip, port, name):
        super().__init__(ip, port, name)

        self.udp_buffers: dict[AddrLike, bytes] = {}
        self.udp_servers: dict[str, UDPConnection] = {}

        self.r: asyncio.StreamReader = None
        self.w: asyncio.StreamWriter = None

        self.transport: _ClientRecvProtocol = None

        self._is_running = False
        
        self._is_receiving = False


    async def subscribe(self, node: str, field: str, handler: Callable | None) -> None:
        await self.send(bytes([
            Datatypes.SUBSCRIBE.value,
            len(node),
            len(field),
            *node.encode(),
            *field.encode(),
        ]))

        if handler is not None:
            if node not in self.handlers:
                self.handlers[node] = {}

            self.handlers[node][field] = handler

            logging.debug(f"ADDED HANDLER {node}:{field}")

    async def unsubscribe(self, node: str, field: str) -> None:
        await self.send(bytes([
            Datatypes.UNSUBSCRIBE.value,
            len(node),
            len(field),
            *node.encode(),
            *field.encode(),
        ]))

    async def post(self, field: str, data: bytes) -> None:
        await self.send(bytes([
            Datatypes.POST.value,
            len(field),
            *field.encode(),
            *data,
        ]))

    async def anon(self, node: str, field: str, data: bytes, force_to_tcp: bool = False) -> None:
        if not force_to_tcp and node in self.udp_servers and self.udp_servers[node].has_connection:
            raw_name = self.name.encode()
            raw_field = field.encode()

            await self.send_udp(bytes([
                DistributedDatatypes.ANON.value,
                len(raw_name),
                len(raw_field),
                *raw_name,
                *raw_field,
                *data
            ]), (self.udp_servers[node].ip, self.udp_servers[node].port))

        elif force_to_tcp or node in self.udp_servers and self.udp_servers[node].has_tried_to_connect:
            await self.send(bytes([
                Datatypes.ANON.value,
                len(node),
                len(field),
                *node.encode(),
                *field.encode(),
                *data
            ]))

        elif node not in self.udp_servers:
            await self.send(bytes([
                Datatypes.GET_UDP_AUTH.value,
                *node.encode()
            ]))

            await self.send(bytes([
                Datatypes.ANON.value,
                len(node),
                len(field),
                *node.encode(),
                *field.encode(),
                *data
            ]))

        else:
            await self.send_udp(bytes([
                DistributedDatatypes.PING.value,
            ]), (self.udp_servers[node].ip, self.udp_servers[node].port))

            counter = 0
            self.udp_servers[node].has_tried_to_connect = True
            while not self.udp_servers[node].has_connection and counter < 100:
                counter += 1
                await asyncio.sleep(0.05)

            if self.udp_servers[node].has_connection:
                raw_name = self.name.encode()
                raw_field = field.encode()

                await self.send_udp(bytes([
                    DistributedDatatypes.ANON.value,
                    len(raw_name),
                    len(raw_field),
                    *raw_name,
                    *raw_field,
                    *data
                ]), (self.udp_servers[node].ip, self.udp_servers[node].port))
            
            else:
                await self.send(bytes([
                    Datatypes.ANON.value,
                    len(self.name),
                    len(field),
                    *node.encode(),
                    *field.encode(),
                    *data
                ]))

    async def rosstat(self) -> None:
        await self.send(bytes([
            Datatypes.ROSSTAT.value,
        ]))


    async def _recv(self, length: int) -> bytes:
        while self._is_receiving:
            await asyncio.sleep(0.003)
            
        self._is_receiving = True
        data = await self.r.readexactly(length)
        self._is_receiving = False
        
        return data
    
    async def _send(self, data) -> None:
        self.w.write(data)
        await self.w.drain()

    async def recv(self):
        try:
            length = await self._recv(4)
            length = struct.unpack(">I", length)[0]
            return zlib.decompress(await self._recv(length))
        except Exception as e:
            print(e)
            return bytes([])
        
    async def send(self, data):
        data = zlib.compress(data)
        length = len(data)
        length = struct.pack(">I", length)

        # while self.sending:
        #     asyncio.sleep(0.01)

        # self.sending = True
        
        if data[0] == 0x01:
            raise Exception

        await self._send(length)
        await self._send(data)
        
        # self.sending = Fals   e


    async def send_udp(self, data: bytes, addr: AddrLike):
        self.transport.sendto(
            struct.pack(">I", len(data)) + data, addr
        )


    async def _tcp_mainloop(self):
        while True:
            data = await self.recv()
            
            if len(data) <= 0:
                await asyncio.sleep(0.05)
                continue
            
            data, datatype = data[1:], data[0]

            try:
                match Datatypes(datatype):
                    case Datatypes.REQUEST_AUTH:
                        logging.debug("GOT REQUEST_AUTH")

                        CREDENTIALS = self.name.encode()

                        await self.send(bytes([
                            Datatypes.SEND_AUTH.value,
                            len(CREDENTIALS),
                            *CREDENTIALS
                        ]))

                        ip, port = self.transport.get_extra_info("sockname")[:2]

                        await self.send(bytes([
                            Datatypes.SEND_UDP_AUTH.value,
                            *ip.encode(),
                            *struct.pack(">H", int(port)),
                        ]))

                    case Datatypes.SEND_UDP_AUTH:
                        logging.debug("GOT SEND_UDP_AUTH")

                        node_name_len = data[0]
                        node_name = data[1:1+node_name_len].decode()

                        if node_name in self.udp_servers:
                            continue

                        ip = data[1+node_name_len:-2].decode()
                        port = struct.unpack(">H", data[-2:])[0]


                        self.udp_servers[node_name] = UDPConnection(
                            ip,
                            port,
                            node_name,
                        )
                        self.udp_buffers[(ip, port)] = b""

                    case Datatypes.SEND_GET:
                        logging.debug("GOT SEND_GET")
                        
                        name_length = data[0]
                        field_length = data[1]

                        data_start = 2+name_length+field_length

                        node_name = data[2:2+name_length].decode()
                        field_name = data[2+name_length:2+name_length+field_length].decode()

                        if node_name not in self.received:
                            self.received[node_name] = {}

                        self.received[node_name][field_name] = data[data_start:]
                        if node_name in self.handlers and field_name in self.handlers[node_name]:
                            await self.handlers[node_name][field_name](data[data_start:])

                    case Datatypes.SEND_POST:
                        logging.debug("GOT SEND_POST")

                    case Datatypes.ERROR:
                        logging.debug("GOT ERROR")
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
                                    self.udp_servers[name] = UDPConnection(
                                        "", -1, name
                                    )
                                    self.udp_servers[name].has_connection = False
                                    self.udp_servers[name].has_tried_to_connect = True

                            case _:
                                logging.error("Got unknown error")

                    case Datatypes.SEND_ANON:
                        logging.debug("GOT SEND_ANON")

                        name_length = data[0]
                        field_length = data[1]

                        data_start = 2+name_length+field_length

                        node_name = data[2:2+name_length].decode()
                        field_name = data[2+name_length:2+name_length+field_length].decode()

                        await self.anon_handlers[field_name](data[data_start:], node_name)

                    case Datatypes.ROSSTAT:
                        self.on_rosstat(json.loads(data.decode()))

                    case _:
                        raise Exception

            except Exception as e:
                logging.exception(e)
                await self.send(bytes([Datatypes.ERROR.value, Errortypes.METHOD_NOT_FOUND.value]))

    async def _udp_mainloop(self):
        while True:
            tasks = []
            addrs = []
            for buf in self.udp_buffers.keys():
                if len(self.udp_buffers[buf]) > 0:
                    addrs.append(buf)
                    tasks.append(
                        self._udp_mainloop_handler(self.udp_buffers[buf], buf)
                    )

            results = await asyncio.gather(*tasks)

            for res, addr in zip(results, addrs):
                self.udp_buffers[addr] = self.udp_buffers[addr][res:]

            await asyncio.sleep(0.01)

    async def _udp_mainloop_handler(self, data: bytes, addr: AddrLike) -> int:
        length = struct.unpack(">I", data[:4])[0]

        data = data[4:4+length]

        datatype, data = data[0], data[1:]

        match DistributedDatatypes(datatype):
            case DistributedDatatypes.PING:
                await self.send_udp(
                    bytes([
                        DistributedDatatypes.PONG.value,
                    ]),
                    addr
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

                data_start = 2+name_length+field_length

                node_name = data[2:2+name_length].decode()
                field_name = data[2+name_length:2+name_length+field_length].decode()

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

        self._is_running = True

        await asyncio.gather(
            self._tcp_mainloop(),
            self._udp_mainloop(),
        )
