# Local model adapters

Ollama native `/api/tags` and `/api/chat`, and compatible `/v1/models` and
`/v1/chat/completions` servers are supported. Choose an installed chat model
explicitly. No weight downloads, services, cloud fallback or training is included.
A loopback endpoint does not prove its backend is local, free or properly licensed.
Review the backend configuration and model license before use.

`ModelRouter.discover()` returns installed/served names and provider-scoped
sanitized errors. Malformed providers contribute no models; healthy providers
remain visible. Empty valid model lists are different from unreachable servers.
`chat_result` returns text, selected provider/model, elapsed seconds and reported
output tokens (None if unreported). `chat` remains a string-returning wrapper.
Invalid/empty/null replies and invalid usage are errors, never successful answers.

Endpoints are copied and read-only, localhost is resolved to literal loopback,
proxies/redirects are disabled, and requests/responses have a 1 MiB encoded cap.
A declared short HTTP body is parsed only within that frame; unread trailing bytes
are discarded with the connection, never reused. Socket timeouts are inactivity
limits; use the fleet supervisor for a hard wall-clock deadline.

`chat_with_memory` quotes reference data in the user prompt, not the system role.
No tool authority follows from prompt formatting. Nothing is saved automatically;
`save_reply_key` explicitly stores the supplied prompt/reply with unverified 0.5
confidence. Caller-provided actor identifiers are not authentication.

The existing `ai_killswitch` is checked before/after inference and before explicit
reply persistence. STOP, invalid stop configuration or unavailable gate code
blocks inference. Discovery stays available for diagnostics. This is cooperative:
it does not terminate an unrelated model server or provide a filesystem sandbox.
Keep GPT_DOUG_AI_BLOCK_ALL, GPT_DOUG_AI_STOP_DIR and
GPT_DOUG_AI_REQUIRE_STOP_DIRECTORY intact when launching child processes.
