"""
Linux eBPF Kernel Monitor for NetStrip
Hooks into the Linux kernel using BCC to trace TCP connections at Ring 0.
This provides a high-assurance verification stream that cannot be bypassed by standard user-space rootkit hooks.
"""

import logging
import threading
import socket
import struct
import subprocess
from typing import Callable, Optional

logger = logging.getLogger(__name__)

# eBPF C Program
bpf_text = """
#include <uapi/linux/ptrace.h>
#include <net/sock.h>
#include <bcc/proto.h>

BPF_PERF_OUTPUT(ipv4_events);

struct ipv4_data_t {
    u32 pid;
    u32 daddr;
    u16 dport;
    char comm[TASK_COMM_LEN];
};

// Hooking tcp_v4_connect return to catch successful or pending outbound connections
int kretprobe__tcp_v4_connect(struct pt_regs *ctx) {
    int ret = PT_REGS_RC(ctx);
    
    // We can filter by return code. 0 is success, -EINPROGRESS is normal for async.
    // For monitoring, we just want to know the attempt occurred.

    struct sock *sk = (struct sock *)PT_REGS_PARM1(ctx);
    if (!sk) return 0;

    struct ipv4_data_t data = {.pid = bpf_get_current_pid_tgid() >> 32};
    bpf_get_current_comm(&data.comm, sizeof(data.comm));

    data.daddr = sk->__sk_common.skc_daddr;
    data.dport = sk->__sk_common.skc_dport;
    
    // dport is network byte order
    data.dport = ntohs(data.dport);

    ipv4_events.perf_submit(ctx, &data, sizeof(data));
    return 0;
}
"""

class EBPFMonitor:
    def __init__(self, callback: Callable):
        self.callback = callback
        self.b = None
        self.is_running = False
        self.thread = None

    def start(self) -> bool:
        """Attempt to compile and inject the eBPF program into the kernel."""
        try:
            from bcc import BPF
        except ImportError:
            # Auto-install attempt if on Linux
            import platform
            if platform.system() == "Linux":
                logger.info("BCC library missing. Attempting automated installation via apt-get...")
                try:
                    subprocess.run(["apt-get", "update"], check=True, capture_output=True)
                    subprocess.run(["apt-get", "install", "-y", "python3-bpfcc", "bpfcc-tools", "linux-headers-generic"], check=True, capture_output=True)
                    from bcc import BPF
                    logger.info("BCC successfully installed and imported.")
                except Exception as e:
                    logger.debug(f"Automated BCC installation failed: {e}. eBPF Monitor disabled.")
                    return False
            else:
                logger.debug("BCC library not available and not on Linux. eBPF Monitor disabled.")
                return False

        try:
            self.b = BPF(text=bpf_text)
            self.b.attach_kretprobe(event="tcp_v4_connect", fn_name="kretprobe__tcp_v4_connect")
            # Note: A complete implementation would also hook tcp_v6_connect.
        except Exception as e:
            logger.error(f"Failed to load eBPF program into kernel: {e}")
            return False

        self.b["ipv4_events"].open_perf_buffer(self._handle_ipv4_event)
        self.is_running = True
        self.thread = threading.Thread(target=self._poll_loop, daemon=True)
        self.thread.start()
        logger.info("Kernel eBPF Monitor successfully hooked tcp_v4_connect.")
        return True

    def stop(self):
        """Cleanly detach the eBPF program."""
        self.is_running = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=1.0)
        
        # BCC cleans up automatically on object destruction, but we can be explicit
        if self.b:
            self.b.cleanup()
            self.b = None
        logger.info("Kernel eBPF Monitor detached.")

    def _poll_loop(self):
        while self.is_running:
            try:
                # 500ms timeout so we can exit cleanly
                self.b.perf_buffer_poll(timeout=500)
            except Exception as e:
                logger.error(f"eBPF polling loop error: {e}")
                break

    def _handle_ipv4_event(self, cpu, data, size):
        try:
            event = self.b["ipv4_events"].event(data)
            ip = socket.inet_ntoa(struct.pack("<I", event.daddr))
            process_name = event.comm.decode('utf-8', 'replace')
            
            event_data = {
                'pid': event.pid,
                'ip': ip,
                'port': event.dport,
                'process_name': process_name,
                'protocol': 'TCP'
            }
            
            # Pass directly to connection monitor callback
            self.callback(event_data)
        except Exception as e:
            logger.error(f"Error parsing eBPF event: {e}")
