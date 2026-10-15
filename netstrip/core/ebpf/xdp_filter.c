#include <uapi/linux/bpf.h>
#include <linux/in.h>
#include <linux/if_ether.h>
#include <linux/if_packet.h>
#include <linux/if_vlan.h>
#include <linux/ip.h>
#include <linux/ipv6.h>

// BPF Map for static, verified ARP entries (Anti-Spoofing)
BPF_HASH(valid_arp_macs, u32, u64); // Key: IPv4 address, Value: MAC address

// Map for dropping known bad raw-socket patterns
BPF_ARRAY(drop_counters, u64, 1);

static inline int parse_ipv4(void *data, void *data_end, u64 *nh_off) {
    struct iphdr *iph = data + *nh_off;
    if ((void*)&iph[1] > data_end)
        return 0;
    *nh_off += iph->ihl * 4;
    return iph->protocol;
}

int netstrip_xdp_prog(struct xdp_md *ctx) {
    void *data_end = (void *)(long)ctx->data_end;
    void *data = (void *)(long)ctx->data;
    struct ethhdr *eth = data;

    // Boundary check
    if ((void *)(eth + 1) > data_end) {
        return XDP_DROP; // Malformed ethernet frame
    }

    // 1. ARP Inspection (Layer 2)
    if (eth->h_proto == bpf_htons(ETH_P_ARP)) {
        // In a full implementation, we parse the ARP payload and check `valid_arp_macs`.
        // If an IP resolves to a MAC that doesn't match our pinned map, we XDP_DROP it.
        // For stealth, we XDP_PASS valid ones instantly.
        return XDP_PASS; 
    }

    // 2. Raw Socket / Bypass Anomaly Drops
    // If a packet violates strict RFC state (often caused by raw socket injections from malware), drop it.
    if (eth->h_proto == bpf_htons(ETH_P_IP)) {
        struct iphdr *iph = data + sizeof(*eth);
        if ((void *)(iph + 1) > data_end) {
            return XDP_DROP; // Corrupted IP header injected directly
        }
        
        // Example stealth rule: Drop any packet claiming to be from localhost on a physical external NIC
        if (iph->saddr == bpf_htonl(INADDR_LOOPBACK)) {
            u64 zero = 0, *val;
            val = drop_counters.lookup(&zero);
            if (val) lock_xadd(val, 1);
            return XDP_DROP;
        }
    }

    // Default: Pass up the kernel stack to let NetStrip's NFQueue Python logic handle standard routing
    return XDP_PASS;
}
