import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)

class EBPFManager:
    """
    Manages the compilation and injection of the eBPF/XDP program directly into the Linux Kernel.
    This provides 'fileless' kernel hooks that are invisible to most standard filesystem AV scans.
    """
    def __init__(self, interface: str):
        self.interface = interface
        self.bpf = None
        self.is_attached = False

    def start(self) -> bool:
        try:
            # We attempt to import bcc. If it fails, the user needs to install it.
            from bcc import BPF
        except ImportError:
            logger.error("BCC (BPF Compiler Collection) is not installed. Deep Kernel Mode unavailable.")
            return False

        try:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            ebpf_c_path = os.path.join(current_dir, "..", "core", "ebpf", "xdp_filter.c")
            
            if not os.path.exists(ebpf_c_path):
                logger.error("XDP C source file not found.")
                return False

            # Compile the C code dynamically in memory and load it into the kernel
            with open(ebpf_c_path, 'r') as f:
                bpf_text = f.read()

            self.bpf = BPF(text=bpf_text)
            
            # Load the XDP function
            xdp_fn = self.bpf.load_func("netstrip_xdp_prog", BPF.XDP)
            
            # Attach to the interface
            self.bpf.attach_xdp(self.interface, xdp_fn, 0)
            self.is_attached = True
            logger.info(f"Successfully attached invisible eBPF XDP hook to {self.interface}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to attach eBPF program: {e}")
            return False

    def stop(self):
        if self.is_attached and self.bpf:
            try:
                self.bpf.remove_xdp(self.interface, 0)
                self.is_attached = False
                logger.info(f"Removed eBPF XDP hook from {self.interface}")
            except Exception as e:
                logger.error(f"Error removing eBPF hook: {e}")
