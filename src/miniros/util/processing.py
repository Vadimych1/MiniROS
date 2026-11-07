from .datatypes import Datatype, NamedComposedDatatype, NamedComposedValue
from multiprocessing.synchronize import Event
from typing import Callable, Any
import multiprocessing as mp
import asyncio
import time

class NoneDatatype(Datatype):
    STATIC_SIZE = 0
    
    @staticmethod
    def encode(data: None) -> bytearray:
        return bytearray([])
    
    @staticmethod
    def decode(data: bytearray) -> Any:
        return None

class PipeProtocol:
    def __init__(self, datatypes: list[type[Datatype] | NamedComposedDatatype]) -> None:
        self._dt = sorted(datatypes, key=lambda x: str(x))
    
    def encode(
        self, 
        data: Datatype | NamedComposedValue | Any,
        t: type[Datatype] | NamedComposedDatatype | None = None
    ) -> bytearray:
        idx = -1
        
        if t is None:
            t = type(data)
        
        try:
            if isinstance(data, NamedComposedValue):
                idx = self._dt.index(data.parent)

            elif t is NamedComposedDatatype or issubclass(t, Datatype):
                idx = self._dt.index(t)

            else:
                raise ValueError("provided 'data' value is not compatible")

        except IndexError:
            raise ValueError("provided data type is not specified in protocol")

        return bytearray([idx, *self._dt[idx].encode(data)])

    def decode(
        self,
        data: bytearray
    ) -> NamedComposedValue | Datatype | Any:
        idx = data[0]
        data = data[1:]
        
        if idx >= len(self._dt):
            raise ValueError(f"incompatible data: type index {idx} out of range [0, {len(self._dt)})")

        return self._dt[idx].decode(data)

class ProcessPipe:
    def __init__(self, conn, protocol: PipeProtocol) -> None:
        self.conn = conn
        self.protocol = protocol
    
    def write(
        self, 
        data: Any, 
        t: type[Datatype] | NamedComposedDatatype | None = None,
    ):
        encoded = self.protocol.encode(data, t)
        self.conn.send_bytes(encoded)
    
    def read(self, timeout: float = 1.0) -> Any:
        if not self.conn.poll(timeout):
            raise TimeoutError()
        
        data = self.conn.recv_bytes()
        return self.protocol.decode(data)

class MinirosPipe:
    def __init__(
        self,
        protocol: PipeProtocol,
        process_function: Callable[..., None],
        duplex: bool = True,
    ) -> None:
        self._proto = protocol
        self._p_func = process_function
        self._duplex = duplex
        
        self.proc: mp.Process | None = None
        self.running = mp.Event()
        self.parent_conn, self.child_conn = mp.Pipe(duplex=duplex)
    
    def start(self, *args):
        if self.proc is not None and self.proc.is_alive():
            return
        
        self.running.set()
        self.proc = mp.Process(target=_process_func, args=(self._p_func, self.child_conn, self.running, self._proto, args), daemon=True)
        self.proc.start()
    
    def stop(self):
        self.running.clear()

        if self.proc:
            self.proc.join(timeout=3.0)
            if self.proc.is_alive():
                self.proc.terminate()
                self.proc.join(timeout=1.0)
    
    def is_alive(self):
        return self.proc is not None and self.proc.is_alive()
    
    def write(
        self, 
        data: Any, 
        t: type[Datatype] | NamedComposedDatatype | None = None,
    ):
        if not self.running.is_set():
            raise BrokenPipeError("attempted write on a closed pipe")
        
        encoded = self._proto.encode(data, t)
        self.parent_conn.send_bytes(encoded)
    
    def read(self, timeout: float = 1.0) -> Any:
        if not self.running.is_set():
            raise BrokenPipeError("attempted read on a closed pipe")
        
        if not self.parent_conn.poll(timeout):
            raise TimeoutError()

        data = self.parent_conn.recv_bytes()
        return self._proto.decode(data)

    async def read_async(self, timeout: float = 1.0) -> Any:
        deadline = time.monotonic() + timeout
        
        while time.monotonic() < deadline:
            if not self.running.is_set():
                return None
            
            try:
                return self.read(timeout=0)
            
            except TimeoutError:
                await asyncio.sleep(0.005)
        
        return None

def _process_func(f, conn, running, protocol: PipeProtocol, args):
    f(ProcessPipe(conn, protocol), running, *args)

#
if __name__ == "__main__":
    from miniros import datatypes

    def handler(pipe: ProcessPipe, running: Event, *args):
        while running.is_set():
            try:
                data = pipe.read(0.2)
            except TimeoutError:
                continue
            
            pipe.write(None, NoneDatatype)
            
            print(data, flush=True)

    protocol = PipeProtocol([
        NoneDatatype,
        datatypes.Bool,
        datatypes.Int,
    ])

    pipe = MinirosPipe(
        protocol,
        handler,
    )

    if __name__ == "__main__":
        pipe.start()
        
        pipe.write(True, datatypes.Bool)
        pipe.write(184018, datatypes.Int)
        
        print(pipe.read(1))

        pipe.stop()    
        pipe.write(184018, datatypes.Int)
