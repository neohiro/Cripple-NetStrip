// Self-contained env tuning: fast delays + no toast throttling for assertions.
process.env.OPENCODE_RESUME_BASE_DELAY_MS ??= "30"
process.env.OPENCODE_RESUME_RATE_LIMIT_BASE_MS ??= "40"
process.env.OPENCODE_RESUME_MAX_DELAY_MS ??= "500"
process.env.OPENCODE_RESUME_NUDGE_DELAY_MS ??= "30"
process.env.OPENCODE_RESUME_TOAST_THROTTLE_MS ??= "0"
import { AutoResumePlugin } from "./auto-resume.mjs"

const ok = (cond, label) => {
  console.log(`${cond ? "PASS" : "FAIL"}  ${label}`)
  if (!cond) process.exitCode = 1
}
const sleep = (ms) => new Promise((r) => setTimeout(r, ms))

function makeClient(state) {
  return {
    app: { log: async () => true },
    tui: { showToast: async ({ body }) => { state.toasts.push(body.message); return true } },
    session: {
      status: async () => ({ data: Object.fromEntries([...state.idleIds].map((id) => [id, { type: "idle" }])) }),
      prompt: async ({ path, body }) => {
        state.prompts.push({ id: path.id, text: body.parts[0].text, model: body.model })
        return { data: { info: {}, parts: [] } }
      },
      abort: async ({ path }) => { state.aborts.push(path.id); return true },
      summarize: async ({ path }) => { state.summarizes.push(path.id); return true },
      messages: async () => ({
        data: [{
          info: { role: "assistant", error: null, providerID: "anthropic", modelID: "claude-test" },
          parts: [{ type: "text", text: "work done" }],
        }],
      }),
    },
  }
}

async function freshState(idleIds = []) {
  const state = { prompts: [], aborts: [], summarizes: [], toasts: [], idleIds: new Set(idleIds) }
  const hooks = await AutoResumePlugin({ client: makeClient(state) })
  return { state, hooks }
}

const ev = (type, properties) => ({ event: { type, properties } })

// ---- Scenario A: transient 5xx -> auto resume with same model -------------
{
  const { state, hooks } = await freshState(["sessA"])
  await hooks.event(ev("message.updated", { info: { role: "assistant", sessionID: "sessA", providerID: "anthropic", modelID: "claude-test" } }))
  await hooks.event(ev("session.error", { sessionID: "sessA", error: { name: "APIError", data: { statusCode: 503, isRetryable: false, message: "upstream error" } } }))
  await sleep(500)
  ok(state.prompts.length === 1, `A: resumed once after 503 (${state.prompts.length})`)
  ok(state.prompts[0]?.text.startsWith("[auto-resume]"), "A: resume prompt tagged")
  ok(state.prompts[0]?.model?.modelID === "claude-test", "A: same model reused")
  // user abort must never be resumed
  const before = state.prompts.length
  await hooks.event(ev("session.error", { sessionID: "sessA", error: { name: "MessageAbortedError", data: { message: "user aborted" } } }))
  await sleep(300)
  ok(state.prompts.length === before, "A: user abort NOT resumed")
}

// ---- Scenario B: 429 with Retry-After honored ------------------------------
{
  const { state, hooks } = await freshState(["sessB"])
  await hooks.event(ev("session.error", { sessionID: "sessB", error: { name: "APIError", data: { statusCode: 429, message: "rate limited", responseHeaders: { "retry-after": "1" } } } }))
  await sleep(600)
  ok(state.prompts.length === 0, "B: no premature retry inside Retry-After window")
  await sleep(900)
  ok(state.prompts.length === 1, `B: retried after Retry-About elapsed (${state.prompts.length})`)
}

// ---- Scenario C/D/E: truncation nudge, auth stop, network UnknownError -----
{
  const { state, hooks } = await freshState(["sessC"])
  await hooks.event(ev("session.error", { sessionID: "sessC", error: { name: "MessageOutputLengthError", data: {} } }))
  await sleep(350)
  ok(state.prompts.length === 1 && state.prompts[0].text.includes("maximum output length"), "C: truncation -> continue nudge")

  await hooks.event(ev("session.error", { sessionID: "sessC", error: { name: "ProviderAuthError", data: { providerID: "x", message: "bad key" } } }))
  await sleep(250)
  ok(state.prompts.length === 1, "D: auth error -> no retry")
  ok(state.toasts.some((t) => t.includes("auth")), "D: auth toast shown")

  await hooks.event(ev("session.error", { sessionID: "sessC", error: { name: "UnknownError", data: { message: "fetch failed: ECONNRESET" } } }))
  await sleep(450)
  ok(state.prompts.length === 2, `E: network UnknownError -> retried (${state.prompts.length})`)
}

// ---- Scenario F: clean completion resets chain ------------------------------
{
  const { state, hooks } = await freshState(["sessF"])
  await hooks.event(ev("message.part.updated", { part: { type: "text", sessionID: "sessF" } }))
  await hooks.event(ev("session.error", { sessionID: "sessF", error: { name: "APIError", data: { statusCode: 500, message: "boom" } } }))
  await sleep(400)
  const afterFirst = state.prompts.length
  await hooks.event(ev("session.idle", { sessionID: "sessF" })) // evaluateIdle sees clean assistant msg
  await sleep(150)
  await hooks.event(ev("session.error", { sessionID: "sessF", error: { name: "APIError", data: { statusCode: 500, message: "boom again" } } }))
  await sleep(400)
  ok(state.prompts.length === afterFirst + 1, `F: chain counter reset lets us retry again (${state.prompts.length})`)
}

// ---- Scenario G/H: stalled stream watchdog + permission guard ---------------
{
  process.env.OPENCODE_RESUME_STALL_TIMEOUT_MS = "120"
  process.env.OPENCODE_RESUME_WATCHDOG_MS = "60"
  const { state, hooks } = await freshState(["stall1", "perm1"])
  const busy = (id) => hooks.event(ev("session.status", { sessionID: id, status: { type: "busy" } }))
  await busy("stall1")
  await busy("perm1")
  await hooks.event(ev("permission.updated", { sessionID: "perm1", title: "run command" }))
  await sleep(700)
  ok(state.aborts.includes("stall1"), "G: stalled session aborted")
  ok(!state.aborts.includes("perm1"), "H: permission-pending session untouched")
  delete process.env.OPENCODE_RESUME_STALL_TIMEOUT_MS
  delete process.env.OPENCODE_RESUME_WATCHDOG_MS
}

console.log(process.exitCode ? "SMOKE TEST FAILED" : "ALL SMOKE TESTS PASSED")


