# Legacy TAK/CoT compatibility and authorization limits

This is a local, synthetic-data exercise environment inspired by open standards and public TAK Product Center references. It does not attempt to modify TAK.gov, bypass enrollment, or access a government TAK deployment.

| Interface | Implementation status | Network / trust boundary |
| --- | --- | --- |
| CoT 2.0 XML `<event><point>…</point></event>` | Tested parse, encode and validation | Local Python stdlib |
| HTTP CoT lab endpoint | Tested, session token + same origin | 127.0.0.1:8080 default |
| SSE (`text/event-stream`) | Tested event snapshots + deltas | Same-origin browser and local gateway |
| CoT legacy UDP | Tested, explicit opt-in via `legacy-udp` | 127.0.0.1:6969 only |
| CoT legacy TCP | Tested, explicit opt-in via `legacy-tcp` | 127.0.0.1:8087 only |
| SQLite | Tested, capped persistent event history and ACK | Operator's local disk |
| Official TAK Server TLS (often 8089) | **NOT implemented or connected** | Requires separate audited mutual TLS client and organization authority |
| TAK.gov website | **NOT manipulated** | Public reference only |

The [TAK Product Center CoreConfig example](https://github.com/TAK-Product-Center/Server/blob/main/src/takserver-core/example/CoreConfig.example.xml) documents TLS inputs and optional TCP/UDP inputs. A production TAK Server protocol involves more than this local test gateway, including enrollment, broker semantics, cert validation, group permissions, and organizational authorization. A local Python TCP/UDP listener is not a TAK Server and must never be represented as one.

Network isolation: the default Python server and legacy adapters bind **127.0.0.1**, with no remote listener and no outbound connection. Docker's internal interface binds wildcard only within the container and publishes exclusively to host 127.0.0.1. Unencrypted local CoT packets are not appropriate for a production network. The browser deliberately labels upstream TAK unavailable.
