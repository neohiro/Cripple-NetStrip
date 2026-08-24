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
        state.prompts.push({ id: path.id, text: body.parts[0].text })
        return { data: {} }
      },
      abort: async () => true,
      summarize: async ({ path }) => { state.summarizes.push(path.id); return true },
      messages: async () => ({ data: [] }),
    },
  }
}

async function fresh(idle = []) {
  const state = { prompts: [], aborts: [], summarizes: [], toasts: [], idleIds: new Set(idle) }
  const hooks = await AutoResumePlugin({ client: makeClient(state) })
  return { state, hooks }
}
const ev = (type, properties) => ({ event: { type, properties } })

// ---- Scenario I: context overflow -> compact -> resume after compacted -----
{
  const { state, hooks } = await fresh(["ovf"])
  await hooks.event(ev("message.updated", { info: { role: "assistant", sessionID: "ovf", providerID: "anthropic", modelID: "m1" } }))
  await hooks.event(ev("session.error", { sessionID: "ovf", error: { name: "UnknownError", data: { message: "input length exceeds context window" } } }))
  await sleep(200)
  ok(state.summarizes.includes("ovf"), "I: compaction triggered on overflow")
  ok(state.prompts.length === 0, "I: no blind retry on overflow")
  await hooks.event(ev("session.compacted", { sessionID: "ovf" }))
  await sleep(3700)
  ok(state.prompts.length === 1 && state.prompts[0].text.startsWith("[auto-resume]"), "I: resumed after compaction")
  // second overflow after already compacting -> give up, no loop
  const before = state.prompts.length
  await hooks.event(ev("session.error", { sessionID: "ovf", error: { name: "UnknownError", data: { message: "prompt too long again differently" } } }))
  await sleep(300)
  ok(state.summarizes.length === 1, "I: repeat overflow does not re-compact")
  ok(state.prompts.length === before, "I: repeat overflow does not resume")
}

// ---- Scenario J: chain cap reached -> give up ------------------------------
{
  process.env.OPENCODE_RESUME_MAX_CHAIN = "2"
  const { state, hooks } = await fresh(["cap"])
  for (let i = 0; i < 5; i++) {
    await hooks.event(ev("session.error", { sessionID: "cap", error: { name: "APIError", data: { statusCode: 503, message: `outage wave ${i}` } } }))
    await sleep(120)
  }
  await sleep(500)
  ok(state.prompts.length <= 3, `J: capped at max_chain resumes (${state.prompts.length})`)
  ok(state.toasts.some((t) => t.toLowerCase().includes("gave up")), "J: give-up toast shown")
  delete process.env.OPENCODE_RESUME_MAX_CHAIN
}

// ---- Scenario K: circuit breaker opens after repeated dead tasks -----------
{
  process.env.OPENCODE_RESUME_MAX_CHAIN = "0"
  process.env.OPENCODE_RESUME_BREAKER_THRESHOLD = "2"
  process.env.OPENCODE_RESUME_TOAST_THROTTLE_MS = "0"
  const { state, hooks } = await fresh(["b1", "b2", "b3"])
  for (const id of ["b1", "b2"]) {
    await hooks.event(ev("session.error", { sessionID: id, error: { name: "APIError", data: { statusCode: 500, message: "down" } } }))
  }
  await sleep(150)
  await hooks.event(ev("session.error", { sessionID: "b3", error: { name: "APIError", data: { statusCode: 500, message: "still down" } } }))
  await sleep(400)
  ok(state.prompts.length === 0, `K: breaker suppressed b3 resume (${state.prompts.length})`)
  ok(state.toasts.some((t) => t.includes("pausing auto-recovery")), "K: breaker toast shown")
  delete process.env.OPENCODE_RESUME_MAX_CHAIN
  delete process.env.OPENCODE_RESUME_BREAKER_THRESHOLD
}

console.log(process.exitCode ? "EXTENDED TESTS FAILED" : "ALL EXTENDED TESTS PASSED")


