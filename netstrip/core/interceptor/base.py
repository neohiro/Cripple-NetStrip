import abc
import logging
from collections.abc import Callable

logger = logging.getLogger("NetStrip.Interceptor")


class PacketInterceptor(abc.ABC):
    """
    Abstract base class for OS-level packet interceptors.
    Responsible for intercepting outbound packets BEFORE they leave the NIC,
    evaluating them via a callback, and dropping or injecting them.
    """

    def __init__(self, callback: Callable[[str, int, str, int, str, bool], bool]):
        """
        callback: function(dst_ip, dst_port, protocol, src_port, src_ip, is_inbound) -> bool (True = Allow, False = Block)
        """
        self.callback = callback
        self.is_running = False

    @abc.abstractmethod
    def start(self):
        """Start the interception loop."""

    @abc.abstractmethod
    def stop(self):
        """Stop interception and release OS hooks."""
