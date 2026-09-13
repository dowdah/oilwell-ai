# WireGuard read-only discovery and topology verification

## Scope and result

This verification used only the approved ECS SSH route, the user-provided Pi
LAN SSH entry, and the user-provided router SSH entry. It made no WireGuard,
route, firewall, Docker, replay, telemetry, database, or service change.

| Logical system | Identity / architecture | WireGuard interface and address |
| --- | --- | --- |
| MBP | current workstation / `arm64` | No `wg` CLI or globally addressed WireGuard interface observable; only `utun` interfaces with IPv6 link-local addresses were visible. |
| Production Edge Pi | `production-edge-pi-01` / `aarch64` | No `wg` command, WireGuard interface, or WireGuard address present. |
| ECS | production ECS / `x86_64` | `wg0` / `10.66.0.1/24` |
| Router (transit only) | production LAN router / `armv7l` | `wgc5` / `10.66.0.2/32` |

The Pi machine identity was verified through its approved LAN entry: hostname,
machine-id SHA-256, architecture, Docker availability, exactly one old Edge
container, and `EDGE_DEVICE_ID=edge-pi-01` all matched the protected target
record. The raw endpoint, host-key material, and full peer configuration remain
outside Git.

## Observed topology

```text
MBP
  no observable local WireGuard address
  │ current LAN route
  ├────────────── Production Edge Pi (no WireGuard interface)
  │                 device_id=edge-pi-01
  │
  └── default gateway ── Router wgc5 10.66.0.2/32
                            ║ WireGuard transit
                            ║
                         ECS wg0 10.66.0.1/24
```

ECS has an explicit route for the Pi LAN subnet through `wg0`. The Pi uses its
LAN default gateway for return traffic; therefore ECS-to-Pi traffic traverses
the ECS/router WireGuard transit and then the router's LAN bridge. The Pi and
ECS are not direct WireGuard peers, and neither is the MBP an observable
direct WireGuard peer in this session. Router peer endpoints and allowed-IP
details are intentionally omitted from this public record.

## Directed reachability checks

Only addresses discovered in the preceding read-only captures were tested.

| Direction | Test | Result |
| --- | --- | --- |
| MBP → ECS `wg0` | ICMP and TCP/22 | PASS |
| MBP → router `wgc5` | ICMP | PASS |
| MBP → Pi approved LAN entry | SSH identity capture | PASS |
| ECS → Pi LAN | ICMP and TCP/22 | PASS |
| Pi → ECS `wg0` | ICMP and TCP/22 | PASS |
| MBP → Pi WireGuard IP | Not applicable: no Pi WireGuard address exists | No test performed |
| Pi WireGuard SSH identity match | Not applicable: no Pi WireGuard address exists | No test performed |

## Production target registration and recommendation

`production-edge-pi-01` is now uniquely registered in the protected,
Git-ignored target record and verified by exact machine identity. The currently
recommended operational endpoint is the record's verified LAN endpoint when
the operator is on that LAN. It is the only verified Pi SSH endpoint and is
not a Pi WireGuard endpoint.

No independent remote Pi endpoint is currently eligible as a primary endpoint:
the router WireGuard address is a transit address, not the Pi, and must not be
substituted for the Pi target. The registered LAN endpoint remains the current
fallback as well as the only usable endpoint. If a future direct Pi WireGuard
endpoint is added, it must first pass the same SSH hostname, machine-id hash,
architecture, and Edge-identity match before it is recorded or preferred.

## Deployment implication

`C1 production preflight tooling: READY` for the validated ECS capture and Pi
target-registration controls. This is not deployment authorization. The
read-only Pi capture found the old Edge container currently running, so the
next authorized maintenance window must start from fresh preflight and prove
the writer/replay state satisfies the Runbook before any C1 deployment action.
