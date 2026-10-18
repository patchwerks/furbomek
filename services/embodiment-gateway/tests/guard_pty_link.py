import os
import pty
import select
import threading
from abc import ABC, abstractmethod
from types import TracebackType
from typing import Self


class PtyLink(ABC):
    _master: int
    _slave: int
    _path: str
    _stop: threading.Event
    _thread: threading.Thread
    _disconnected: bool

    def __enter__(self) -> Self:
        master, slave = pty.openpty()
        self._master = master
        self._slave = slave
        self._path = os.ttyname(slave)
        self._stop = threading.Event()
        self._disconnected = False
        self._before_start()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self._stop.set()
        self._thread.join(timeout=1)
        os.close(self._slave)
        if not self._disconnected:
            os.close(self._master)

    def disconnect(self) -> None:
        self._stop.set()
        self._thread.join(timeout=1)
        os.close(self._master)
        self._disconnected = True

    @property
    def path(self) -> str:
        return self._path

    def _write(self, data: bytes) -> None:
        _ = os.write(self._master, data)

    def _disconnect_from_worker(self) -> None:
        self._stop.set()
        os.close(self._master)
        self._disconnected = True

    def _before_start(self) -> None:
        return

    def _run(self) -> None:
        buffer = bytearray()
        while not self._stop.is_set():
            ready, _, _ = select.select((self._master,), (), (), 0.01)
            if ready:
                buffer.extend(os.read(self._master, 64))
                self._consume(buffer)

    @abstractmethod
    def _consume(self, buffer: bytearray) -> None: ...
