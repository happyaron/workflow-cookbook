# Running Workflow (ultracode) through a non-Claude backend

Operator notes, not model-facing. Everything the model needs is in SKILL.md.

## What the harness does, and what the model must do

Harness side (model-agnostic, nothing to port):
- The Workflow tool, its JS sandbox, pipeline/parallel scheduling, concurrency cap,
  journal, resume, progress UI, `/workflows`, the ultracode on/off system reminders,
  the `workflow-authoring` skill text.

Model side (what differs between models):
- Deciding when to invoke Workflow and loading the skills first.
- Writing a script that parses (meta literal, no TS, no Date.now).
- Choosing pipeline vs parallel, model tiers, and prompts that return raw data.
- Reading journal.jsonl and resuming instead of blindly re-running.

The cookbook skill targets exactly that model-side gap.

## Backend capabilities the Workflow tool depends on

Confidence tags per the user's rules. Verify against your proxy before relying on it.

| Requirement | Why | Tag |
|---|---|---|
| Anthropic Messages API shape (`/v1/messages`, `tools`, `tool_use`/`tool_result` blocks) | Claude Code speaks only this protocol | [KNOWN], high |
| Forced tool choice (`tool_choice: {type:'tool', name:'StructuredOutput'}`) | `agent(..., {schema})` forces a StructuredOutput tool call and validates the input; without forcing, schema agents return prose and `agent()` retries or returns null | [INFERRED] from the skill text, medium |
| Multiple tool definitions per request, parallel tool_use blocks | subagents use Bash/Read/Grep/etc in one turn | [KNOWN], high |
| Streaming (SSE) | the UI streams; non-streaming proxies usually still work but progress is blank | [KNOWN], medium |
| Large context (100k+) | subagents read files; small-context models drop tool results | [COMMON] |
| Ignores or accepts unknown params (`effort`, thinking, cache_control, betas) | the harness sends Anthropic-specific fields | [INFERRED], medium |

If `tool_choice` forcing is unsupported, scripts should avoid `schema` and instead
ask for "return ONLY a JSON object" and `JSON.parse` in the script. That loses
validation and retries; treat it as a fallback.

## Environment variables for model routing

These let `opts.model: 'haiku' | 'sonnet' | 'opus' | 'fable'` in scripts resolve
to your in-house IDs, so the cookbook's tier constants stay portable.

| Variable | Effect | Tag |
|---|---|---|
| `ANTHROPIC_BASE_URL` | point the harness at your proxy | [KNOWN], high |
| `ANTHROPIC_AUTH_TOKEN` or `ANTHROPIC_API_KEY` | credential sent to the proxy | [KNOWN], high |
| `ANTHROPIC_MODEL` | default session model | [KNOWN], high |
| `ANTHROPIC_DEFAULT_HAIKU_MODEL` | what alias `haiku` resolves to | [KNOWN], medium |
| `ANTHROPIC_DEFAULT_SONNET_MODEL` | what alias `sonnet` resolves to | [KNOWN], medium |
| `ANTHROPIC_DEFAULT_OPUS_MODEL` | what alias `opus` resolves to | [KNOWN], medium |
| `ANTHROPIC_DEFAULT_FABLE_MODEL` | what alias `fable` resolves to. Not in the env-var reference as of 2026-10-10 (only HAIKU/SONNET/OPUS/DEFAULT were listed), so treat it as [INFERRED]: harmless if unrecognised, but do not rely on it. | [INFERRED], medium |
| `CLAUDE_CODE_SUBAGENT_MODEL` | default model for subagents, and so for `agent()` calls with no `model` | [KNOWN], medium |

Confirm the exact names with `claude --help` and the current settings docs; the
medium-confidence ones have been renamed before.

Observed 2026-10-10 on the current proxy: a subagent requested with alias
`haiku` was sent as `claude-haiku-4-5-20251001` and the proxy answered
`422 model not found`. So the alias remap is not optional here; without it the
cheap tier, the `claude-code-guide` agent, and `prompt`/`agent`-type hooks fail.

Suggested mapping:

```
ANTHROPIC_DEFAULT_HAIKU_MODEL=<inhouse-small>
ANTHROPIC_DEFAULT_SONNET_MODEL=<inhouse-mid>
ANTHROPIC_DEFAULT_OPUS_MODEL=<inhouse-large>
ANTHROPIC_DEFAULT_FABLE_MODEL=<inhouse-top>
ANTHROPIC_MODEL=<inhouse-large>
CLAUDE_CODE_SUBAGENT_MODEL=<inhouse-mid>
```

With that in place, scripts keep `MODEL_CHEAP = 'haiku'` etc. and the same
script runs on Claude or on your API by changing env only. Whether the top tier
resolves as the alias `fable` or as the explicit ID in `MODEL_TOP` depends on
whether `ANTHROPIC_DEFAULT_FABLE_MODEL` is honoured; see the quality section
below.

## Why under-sized workflows happen, and the operator-side fixes

Observed on the in-house model: 2 or 3 agents in one stage, sometimes 3 then 2,
then the main context finishes the job itself and long tasks degrade. Causes
visible in the harness text the model reads, in order of leverage:

1. The Workflow tool description carries a size guideline ("medium, keep
   workflows under 10 agents") and says it is adjustable under "Dynamic workflow
   size" in `/config`. [KNOWN] Raise or remove it. An instruction-following model
   treats it as a ceiling.
2. The tool description frames Workflow as expensive and opt-in-only. The
   cookbook's sections 1 to 3 counter that with the dispatcher rule, a
   work-proportional sizing rule, and an explicit "large fan-out is safe" section.
3. Scale is left to judgment in the reference text. The cookbook replaces it with
   one agent per work item, capped, and raised by `budget.total`. Put a `+Nk`
   budget in heavy prompts so `budget.total` is set; the model then sizes by
   arithmetic. Note this can also over-fire the other way: a fixed six-agent
   floor on a two-file change is as wrong as two agents on an audit, which is why
   the count is per step, not global.
4. Disposition is a training effect, not a knowledge gap. If you control
   training, the cookbook templates are a seed for supervised task-to-script
   pairs. Prompt levers above come first.

The CLAUDE.md "Ultracode sizing" block repeats the dispatcher rule and floors so
they are in context every turn, not only after the skill loads.

## Subagents messaging main

Observed 2026-10-10 in a real workflow run: 14 subagents made 16 `SendMessage`
calls addressed `to: "main"`, with zero `<cross-session-message>` markers in the
transcript. So these are in-process subagents using the background-agent escape
hatch, and every one wakes the main loop. One of them carried a retraction of a
finding, delivered out-of-band and therefore invisible to the script's collected
results. Prompt-level fix: `AGENT_RULES` appended to every prompt in the
cookbook templates. Enforcement-level fix: the staged hook denies subagent
`SendMessage` while armed. [KNOWN from the transcript, high]

## Turning ultracode on

Either include the word `ultracode` in a prompt (per-turn opt-in) or enable it for
the session so the harness emits the "ultracode is on" reminder. The cookbook's
section 0 mirrors the harness rules, so a model that follows it behaves the same
way Claude does.

## Smoke test

Run this once on the new backend. It exercises meta parsing, schema forcing,
pipeline, model override, and log():

```js
export const meta = { name: 'smoke', description: 'Backend smoke test', phases: [{ title: 'Ping' }] }
const S = { type: 'object', properties: { n: { type: 'integer' }, model: { type: 'string' } }, required: ['n'] }
const out = await pipeline([1, 2, 3],
  n => agent(`Return n=${n} and the model name you believe you are.`, { phase: 'Ping', schema: S, model: n === 3 ? 'haiku' : undefined }),
  r => r ? { ...r, ok: true } : null)
log(`got ${out.filter(Boolean).length}/3`)
return out
```

Pass: three objects with integer `n`. Fail modes: all null means schema forcing
is broken; parse error means the model mangled the script; only the first returns
means concurrency or streaming issues on the proxy.

## Quality-preserving top tier

The cookbook's `MODEL_TOP` is the alias `fable`, for final synthesis, design
judging, and decisive verification. Keep cheaper tiers for routine work, not for
decisions whose mistakes determine the final result. For disputed findings,
escalate to a top-tier verifier.

Confirmed with the operator on 2026-10-10: the proxy serves exactly
`gpt-6-luna`, `gpt-6.1-sol` and `gpt-6-astra`. The four aliases therefore resolve
as follows, and every tier now tracks its env var rather than a hardcoded ID:

| Alias | Env var | Served ID |
|---|---|---|
| `haiku` | `ANTHROPIC_DEFAULT_HAIKU_MODEL` | `gpt-6-luna` |
| `sonnet` | `ANTHROPIC_DEFAULT_SONNET_MODEL` | `gpt-6.1-sol` |
| `opus` | `ANTHROPIC_DEFAULT_OPUS_MODEL` | `gpt-6.1-sol` |
| `fable` | `ANTHROPIC_DEFAULT_FABLE_MODEL` | `gpt-6-astra` |

`ANTHROPIC_DEFAULT_FABLE_MODEL` was not in the env-var reference as of
2026-10-10, so the `fable` alias is the one link in this chain that is still
unverified. Probe it once (a single request with `"model":"fable"`). If the alias
does not resolve, the fallback is to write the served ID `gpt-6-astra` into
`MODEL_TOP` in the templates, at the cost of the env portability described above.

A `behavesAs` profile changes client handling, not the underlying model's quality.
Do not silently downgrade the top tier if the endpoint is unavailable.
