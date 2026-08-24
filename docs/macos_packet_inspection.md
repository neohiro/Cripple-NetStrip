# macOS Packet Interception — Architecture Notes

## Current state (PF anchor)
The existing `netstrip/platform/macos.py` uses PF anchors to block IPs at
the kernel level. This works for policy enforcement but provides:
- ❌ No per-packet inspection (can't count bytes or read SNI)
- ❌ No per-app attribution (rules are IP-based, not process-based)
- ✅ Zero latency impact (kernel-level filtering)
- ✅ No special entitlements required

## Target state (NEFilterDataProvider)

Apple's NetworkExtension framework provides user-space packet processing:

```
┌────────────────────────────────────────────┐
│ NetStrip.app (Kivy/Python)                 │
│   └─ pyobjc → NSXPCConnection              │
│        └─ FilterProvider (Swift)           │
│             ├─ NEFilterDataProvider         │
│             │   ├─ handleInboundData       │
│             │   ├─ handleOutboundData      │
│             │   └─ verdict: allow/drop    │
│             └─ NEFilterControlProvider     │
│                  └─ Rules from Python IPC  │
└────────────────────────────────────────────┘
```

### Requirements
1. **Swift helper app** containing the NEFilterDataProvider extension
2. **App Group entitlement** for IPC between Python and Swift helper
3. **Signed with Developer ID** + Network Extension entitlement profile
4. **System Extension approval** by user in System Preferences

### Python ↔ Swift IPC protocol
```
Python writes rules to shared file:
  ~/.NetStrip/macos_filter_rules.json
  [{"action": "block", "ip": "1.2.3.4", "port": null, "proto": null}, ...]

Swift helper watches file via dispatch source, updates filter rules.

Python reads bandwidth stats from shared file:
  ~/.NetStrip/macos_bandwidth.json
  {"com.apple.Safari": {"sent": 1024, "recv": 4096}, ...}
```

### Implementation phases

| Phase | Scope | Effort |
|---|---|---|
| Phase 0 | Document architecture (this file) | Done |
| Phase 1 | Swift XPC helper skeleton + pyobjc bridge | ~2 weeks |
| Phase 2 | Bandwidth-only mode (count, don't block) | ~1 week |
| Phase 3 | Block/allow verdicts via JSON rule file | ~2 weeks |
| Phase 4 | Integration into buildozer/p4a packaging | ~1 week |

### Why not pyobjc directly?
NEFilterDataProvider requires implementing an Objective-C/Swift protocol
with callback methods invoked on internal Apple queues. While pyobjc can
bridge Objective-C classes, the NetworkExtension framework requires:
- A `.appex` extension bundle embedded in the host app
- Entitlements signed by Apple (Developer ID + NE entitlement)
- System Extension lifecycle management (activation, deactivation)

These cannot be satisfied from pure Python. The helper must be a native
Swift binary distributed alongside the Kivy app.
