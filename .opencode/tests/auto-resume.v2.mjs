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
    config: {
      providers: async () => ({
        data: {
          providers: [
            { id: "anthropic", models: { "claude-4-opus": {}, "claude-4-haiku": {} } },
            { id: "openai", models: { "gpt-5": {}, "text-embedding-3": {} } },
          ],
        },
      }),
    },
    session: {
      status: async () => ({ data: Object.fromEntries([...state.idleIds].map((id) => [id, { type: "idle" }])) }),
      prompt: async ({ path, body }) => {
        state.prompts.push({ id: path.id, text: body.parts[0].text, model: body.model })
        return { data: {} }
      },
      abort: async () => true,
      summarize: async ({ path }) => { state.summarizes.push(path.id); return true },
      messages: async () => ({
        data: [{
          info: { role: "assistant", error: null, providerID: "openai", modelID: "gpt-5" },
          parts: [{ type: "text", text: "done" }],
        }],
      }),
      message: async ({ path }) => ({
        data: { parts: [{ type: "text", text: state.msgStore[path.messageID] ?? "" }] },
      }),
      postSessionByIdPermissionsByPermissionId: async ({ path, body }) => {
        state.permResponses.push({ sessionID: path.id, permissionID: path.permissionID, response: body.response })
        return { data: true }
      },
    },
  }
}

async function fresh(idle = []) {
  const state = {
    prompts: [], aborts: [], summarizes: [], toasts: [], permResponses: [],
    idleIds: new Set(idle), msgStore: {},
  }
  const hooks = await AutoResumePlugin({ client: makeClient(state) })
  return { state, hooks }
}
const ev = (type, properties) => ({ event: { type, properties } })

// ---- L: quota/free-tier -> automatic model rotation ------------------------
{
  const { state, hooks } = await fresh(["qA", "qB"])
  await hooks.event(ev("message.updated", { info: { role: "assistant", sessionID: "qA", providerID: "anthropic", modelID: "claude-4-opus" } }))
  await hooks.event(ev("session.error", { sessionID: "qA", error: { name: "UnknownError", data: { message: "Free usage exceeded, subscribe to Go" } } }))
  await sleep(400)
  ok(state.prompts[0]?.id === "qA" && state.prompts[0]?.model?.modelID === "claude-4-haiku",
    `L: quota -> rotated to anthropic sibling (${JSON.stringify(state.prompts[0]?.model)})`)
  // exhaust the sibling too -> must skip cooled-down opus AND non-chat embedding model
  await hooks.event(ev("message.updated", { info: { role: "assistant", sessionID: "qB", providerID: "anthropic", modelID: "claude-4-haiku" } }))
  await hooks.event(ev("session.error", { sessionID: "qB", error: { name: "APIError", data: { statusCode: 402, message: "billing quota exceeded" } } }))
  await sleep(400)
  const second = state.prompts.find((x) => x.id === "qB")?.model
  ok(second?.providerID === "openai" && second?.modelID === "gpt-5",
    `L: cross-provider fallback honors cooldowns (${JSON.stringify(second)})`)
}

// ---- M: permission autopilot -------------------------------------------------
{
  const { state, hooks } = await fresh([])
  let pid = 0
  const ask = (type, title, metadata) =>
    hooks.event(ev("permission.updated", {
      id: `p${++pid}`, sessionID: "permSess", type, title, metadata: metadata ?? {},
    }))
  await ask("bash", "Run command", { command: "npm test" })
  await ask("bash", "Run command", { command: "rm -rf ./node_modules" })
  await ask("edit", "Edit file src/app.py")
  await ask("webfetch", "Fetch https://example.com")
  await ask("mystery_type", "Unknown thing")
  await sleep(300)
  const byPerm = Object.fromEntries(state.permResponses.map((r) => [r.permissionID, r.response]))
  ok(byPerm.p1 === "once", "M: safe bash approved")
  ok(byPerm.p2 === "reject", "M: dangerous bash rejected (agent unblocks)")
  ok(byPerm.p3 === "once", "M: edit approved")
  ok(byPerm.p4 === "once", "M: webfetch approved")
  ok(byPerm.p5 === undefined, "M: unknown type left for human in safe mode")
}

// ---- N: todo drive + wrap-up proposals --------------------------------------
{
  const todosOpen = [
    { id: "t1", status: "completed", content: "a", priority: "high" },
    { id: "t2", status: "pending", content: "b", priority: "high" },
  ]
  const todosDone = [
    { id: "t1", status: "completed", content: "a", priority: "high" },
    { id: "t2", status: "completed", content: "b", priority: "high" },
  ]
  const { state, hooks } = await fresh(["td"])
  await hooks.event(ev("todo.updated", { sessionID: "td", todos: todosOpen }))
  await hooks.event(ev("session.idle", { sessionID: "td" })) // clean turn, unfinished todos
  await sleep(400)
  ok(state.prompts.some((p) => p.text.includes("todo list still has unfinished")), "N: todo-drive nudge sent")
  await hooks.event(ev("todo.updated", { sessionID: "td", todos: todosDone }))
  await hooks.event(ev("session.idle", { sessionID: "td" }))
  await sleep(400)
  ok(state.prompts.filter((p) => p.text.includes("wrap-up")).length === 1, "N: single proposal prompt after completion")
  await hooks.event(ev("session.idle", { sessionID: "td" }))
  await sleep(300)
  ok(!state.prompts.some((p) => p.text.includes("wrap-up")) || state.prompts.filter((p) => p.text.includes("wrap-up")).length === 1,
    "N: proposals sent exactly once")
}

// ---- O: debug nudge after consecutive tool failures --------------------------
{
  const { state, hooks } = await fresh(["dbg"])
  const toolPart = (status) => ev("message.part.updated", {
    part: { type: "tool", sessionID: "dbg", state: { status }, tool: "bash" },
  })
  for (let i = 0; i < 3; i++) await hooks.event(toolPart("error"))
  await sleep(400)
  ok(state.prompts.filter((p) => p.text.includes("root cause")).length === 1, "O: debug nudge after 3 failures")
  await hooks.event(toolPart("error"))
  await sleep(200)
  ok(state.prompts.filter((p) => p.text.includes("root cause")).length === 1, "O: armed once per streak")
  await hooks.event(toolPart("completed"))
  await hooks.event(toolPart("error"))
  await hooks.event(toolPart("error"))
  await sleep(200)
  ok(state.prompts.filter((p) => p.text.includes("root cause")).length === 1, "O: streak reset on success")
}

// ---- P: max-nudges cap + real-user-message scope reset ------------------------
{
  process.env.OPENCODE_AUTOPILOT_MAX_NUDGES = "1"
  const { state, hooks } = await fresh(["rs"])
  const todo = [{ id: "t", status: "pending", content: "x", priority: "low" }]
  await hooks.event(ev("todo.updated", { sessionID: "rs", todos: todo }))
  await hooks.event(ev("session.idle", { sessionID: "rs" }))
  await sleep(350)
  ok(state.prompts.length === 1, "P: first drive nudge allowed")
  await hooks.event(ev("session.idle", { sessionID: "rs" }))
  await sleep(350)
  ok(state.prompts.length === 1, "P: cap blocks further nudges")
  // real human message -> new task scope -> cap budget restored
  state.msgStore.um1 = "New task: please refactor the auth module"
  await hooks.event(ev("message.updated", { info: { role: "user", sessionID: "rs", id: "um1" } }))
  await sleep(50)
  await hooks.event(ev("session.idle", { sessionID: "rs" }))
  await sleep(350)
  ok(state.prompts.length === 2, "P: new user task restores nudge budget")
  // our own injected message (tagged) must NOT reset scope
  state.msgStore.um2 = "[auto-resume] The todo list still has unfinished items..."
  await hooks.event(ev("todo.updated", { sessionID: "rs", todos: [{ id: "t2", status: "pending", content: "y", priority: "low" }] }))
  await sleep(20)
  await hooks.event(ev("message.updated", { info: { role: "user", sessionID: "rs", id: "um2" } }))
  await hooks.event(ev("session.idle", { sessionID: "rs" }))
  await sleep(350)
  // if the tagged message had been misjudged as human, scope would reset and
  // another drive-nudge would fire despite the exhausted cap -> stays at 2.
  ok(state.prompts.length === 2, "P: injected message does not reset scope (cap still holds)")
  delete process.env.OPENCODE_AUTOPILOT_MAX_NUDGES
}

console.log(process.exitCode ? "V2 TESTS FAILED" : "ALL V2 TESTS PASSED")


