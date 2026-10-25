---
name: workflow-cookbook
description: Prescriptive cookbook for Claude Code's Workflow tool (ultracode). Load when the user says "ultracode", "use a workflow", "fan out agents", gives a "+Nk" budget, or asks for a thorough review/audit/research/migration. Gives sizing rules, copy-ready script templates, canned lens lists, a pre-flight checklist, and the cost-tier model map so a script is large enough and runs on the first try.
---

# Workflow cookbook

Companion to the built-in `workflow-authoring` skill. That skill is the API
reference; this one tells you how big to go and gives you the scripts. Load BOTH
before writing a script: `workflow-authoring` first, then this file.

## 0. Decision rule

Call the Workflow tool ONLY if one of these is true:

- The prompt contains `ultracode`, or a system-reminder says ultracode is on.
- The prompt contains a token budget like `+300k` or `+1m`.
- The user said "use a workflow", "run a workflow", "fan out agents", or "orchestrate with subagents".
- A slash command's instructions say to call Workflow.

Otherwise do not call it. Say in one line what a workflow could do and offer it.

When ultracode IS on, every substantive task goes through a workflow. Solo work is
limited to conversational replies and trivial single-file edits.

## 1. The dispatcher rule (most important section)

When ultracode is on, your own context is a DISPATCHER, not a worker. It does
exactly four things: scout the work list, author and launch workflows, read
results, relay to the user. The quality of long tasks collapses when the
dispatcher starts doing the work itself, because its context fills with file
contents and it loses track of the overall job.

Hard limits on inline work while ultracode is on:

- Read at most 3 files yourself, and only to build the work list for `args`.
- Edit at most 1 file yourself, and only a trivial change.
- Write at most one paragraph of analysis yourself. Longer analysis is a workflow.
- NEVER "finish the rest yourself" after a workflow returns. If rejected files or
  confirmed findings remain, that is a new workflow over them, not inline work,
  and never a phase that belonged in the script (section 12).
- NEVER start the work yourself while a workflow is still running. Waiting is
  part of dispatching. Section 13 says how to wait.

A heavy job is ONE workflow. Its script runs every phase the job needs and
hands each phase's result to the next inside the script, as a variable. The
dispatcher never relays results between phases; that relay is exactly where
context fills and quality drops. One launch, one wait, one result.

| Phase inside the script | Pattern from | Hands the next phase |
|---|---|---|
| Understand | 9b | an overview plus the file list the job touches |
| Design | 9c | one plan with the files to change and the tests to run |
| Implement | 9e | verified diffs, retried once in-script when refuted |
| Integrate | 9g | all accepted diffs applied together, built and tested |
| Review | 9a | confirmed findings over the diffs |
| Report | one top-tier agent | what to apply, what was left out, and why |

Template 9g is this shape end to end. Do not break it into one invocation per
phase to "stay in the loop". If a later phase goes wrong, edit the script and
resume: every earlier phase is cached, so nothing is lost by running them
together. Split into separate workflows only at a point where the USER must
choose before the next phase can be specified, for example picking between two
designs with different cost, or where the next phase's work list cannot be
derived by the script from the previous result. Those are rare.

## 2. Sizing follows the work, not a constant

Never decide size by feel, and never apply one global number. Two rules:

1. **Each step's agent count is a function of that step's own work items**, with
   a ceiling. Three modules to read means three readers. Two files to review
   means two lenses, not six. Counts differ from step to step because the work
   does. Work out the list for each step, then take one agent per item.
2. **The budget raises the ceiling, never lowers it.** When the operator gave
   `+Nk`, size up toward it; the runtime enforces it as a hard limit. With no
   budget, the ceiling column below applies.

```js
const clamp = (n, lo, hi) => Math.max(lo, Math.min(hi, n))
const B = budget.total || 0                        // 0 when no +Nk was given
const ceiling = (base) => B ? Math.max(base, Math.floor(B / 100_000)) : base
```

| Task shape | Count = one per | Small job | Heavy job ceiling |
|---|---|---|---|
| Review / audit | file batch (BATCH files), times lens | 1 lens | 10 lenses |
| Understand | module / package | 1 reader | 6 readers |
| Design | distinct angle | 2 proposals | 5 proposals, 1 judge per criterion (3) |
| Research | sweep mode (7 canned) | 3 modes | 7 modes + 1 critic |
| Migrate / implement | changed file | 1 transformer + 1 verifier | every file |
| Discovery loop | lens, each round | full lens set | cap 8 rounds |

Verification is one verifier per finding, asked every question in one call, plus
a Fable escalation for the findings where a wrong verdict costs most (section 9a).
Do not fan several lens-verifiers over one finding and vote: lenses asking
different questions are not independent checks, and a 2-of-3 vote drops real
bugs that are merely hard to reproduce or low in impact. Everything else scales
with its step's work list.

**A step exists only if it produces something the next step consumes.** The phase
lists under section 9 are the shape for that kind of task, not a mandated number
of steps. A two-file change may be one fan-out plus one synthesis. A full audit
may be five steps. Let the work decide the step count, subject to one invariant:
every load-bearing claim is checked by something independent of what produced it.
A single fan-out with no check of any kind is the shortcut to avoid, not the
short workflow.

Agents per workflow therefore range widely: a handful for a small task, 20 to 80
for a heavy one. Both are correct when the count matches the work.

## 3. Why a large fan-out is safe

The runtime is built for it. None of these require caution on your part:

- Concurrency is capped automatically (about 10 to 16 at once). Passing 100 items
  just queues them. You do not manage parallelism.
- `agent()` never throws on a failed subagent. It returns `null`. `parallel()`
  never rejects. A throwing pipeline stage drops only that item.
- The budget is a hard ceiling. When it is exhausted `agent()` throws, the script
  stops, and you still get everything completed so far via the journal.
- Resume caches every completed `agent()` call. Editing and re-running a 60-agent
  script re-runs only the changed tail.
- Hard caps exist (1000 agents per run, 4096 items per call). You cannot run away.

A 50-agent workflow is not riskier than a 3-agent one. It only takes longer.

## 4. Hybrid pattern: scout, then orchestrate

Build the concrete work list inline first (Glob, Grep, `git diff --name-only`,
`ls`), within the section 1 limits, then pass it as `args`:

```
Workflow({ script: "<script>", args: { files: ["src/a.ts", "src/b.ts"], question: "..." } })
```

`args` is a real JSON value in the tool call, never a JSON-encoded string.

## 5. Hard rules the parser and sandbox enforce

- `export const meta = {...}` is the FIRST statement and a PURE LITERAL. No
  variables, calls, template strings, or spreads inside it.
- `meta.name` and `meta.description` are required. `meta.phases[].title` must
  match `phase('...')` and `opts.phase` strings exactly.
- Plain JavaScript. No TypeScript syntax. Top-level `await` and `return` work.
- FORBIDDEN: `Date.now()`, `Math.random()`, `new Date()` with no args, `import`,
  `require`, `fs`, `fetch`, `process`.
- Schemas: root is `{type:'object', properties:{...}}`; `required` is a subset of
  `properties`.
- `agent()` can return `null`. Always `.filter(Boolean)` arrays and `?.` singles.
- `parallel()` takes thunks: `items.map(x => () => agent(...))`.
- `pipeline()` stage callbacks receive `(prevResult, originalItem, index)`.

Shape rules that keep a generated script parseable. The parse error observed on
this backend, `Unexpected token` at column 0 of a `phase(...)` line, is what
breaking these produces. It is not a TypeScript error, whatever the harness
message suggests:

- One `agent()` call per statement, named: `const read = m => agent(...)`. Then
  `await fan(items, read)`. Never write `(await parallel(items.map(x => () =>
  agent(...)))).filter(Boolean)` inline; its five closing parens are where the
  count goes wrong. `fan` is defined in section 9 and does the same thing.
- No backtick inside prompt text. Name files and symbols bare: `Read src/a.ts`,
  not `Read \`src/a.ts\``. A stray backtick ends the template literal and the
  parser resumes mid-sentence several lines later.
- No nested template literal inside `${...}`. Compute the piece into a `const`
  on the line above and interpolate the name.
- Prompts are template literals, never single-quoted strings, so apostrophes in
  prose cannot end the string.
- Never start a line with `(`, `[`, or a backtick. The parser glues it to the
  previous line. Begin lines with `const`, `let`, `await`, `if`, `for`, `log`, or
  `return`.
- Run the checker before calling Workflow (section 11, item 16).

Reading a parse error. The line and column are where the parser gave up, which
is usually AFTER the fault:

| Message | At | Cause | Fix |
|---|---|---|---|
| `Unexpected token` | column 0 of a line that begins a new statement, such as `phase('Design')` or `const x` | an unclosed `(`, `[`, or `{` in the statement above, or a stray backtick that swallowed the line ends | balance the previous statement; search the prompt text above for backticks |
| `Unterminated template` | end of script | odd number of backticks | find the backtick inside prompt text |
| `Unterminated string constant` | inside a line | apostrophe inside a single-quoted string | make it a template literal |
| `Unexpected token` | at a `:` after a parameter name | TypeScript annotation | delete the annotation |
| `Unexpected token` | at `<` or `as` | TypeScript generic or cast | delete it |
| meta error | line 1 | non-literal `meta` | inline every value |

The checker in section 11 uses node, whose wording differs from the harness
parser: `Unexpected identifier 'phase'` for the unclosed-bracket case and
`missing ) after argument list` for a backtick inside prompt text. Read the line
number it prints and apply the same fixes.

## 6. pipeline vs parallel

Default to `pipeline`. Use `parallel` as a barrier only when the next stage needs
ALL prior results together: dedup/merge across the set, early exit on zero total,
or a prompt that compares against "the other findings". Flatten/map/filter between
stages is not a barrier; do it inside a pipeline stage.

## 7. Cost tiers

Declare these right after `meta` in every script. The operator maps the aliases
to real backend model IDs via environment variables, so scripts stay portable.

```js
const MODEL_CHEAP = 'haiku'    // search, grep, reformat, sweeps
const MODEL_MID   = 'sonnet'   // finders, readers, transformers, single-lens checks
const MODEL_HIGH  = 'opus'     // finding verifiers, design proposals, tricky verification
const MODEL_TOP   = 'fable'    // final synthesis, judges, scoring, decisive verification
```

Quality takes priority at the stages that decide the outcome. Keep Fable for
final synthesis, design judges, scoring competing outputs, and decisive
verification. Routine readers, finders, and transformers still use cheaper tiers.
Escalate ambiguous or disputed findings to a Fable verifier rather than deciding
by cheap-model majority alone. Do not silently replace the top tier with Opus to
save cost. If the Fable endpoint is unavailable, report the blocked stage and
request an approved replacement.

All four are aliases on purpose. The operator maps them to real backend model IDs
through environment variables, so a single env change re-points every tier and no
script needs editing. `MODEL_TOP` uses the `fable` alias, which resolves through
`ANTHROPIC_DEFAULT_FABLE_MODEL`. Do not paste a raw model ID into these constants
instead; it would break that portability.

A client-side `behavesAs` profile does not establish equivalent model quality, so
never treat a `behavesAs`-labelled picker entry as a substitute for the alias.

To use the session model, omit `model`. Use `effort` only if the operator has
confirmed the backend accepts it.

## 8. Canned lens lists

Fan-out needs N distinct prompts. Do not invent them each time; slice these.

```js
const REVIEW_LENSES = [
  'correctness: logic errors, off-by-one, wrong conditions, unhandled states',
  'error handling: swallowed errors, missing propagation, misleading messages',
  'concurrency: races, missing awaits, shared mutable state, ordering',
  'security: injection, authz gaps, secrets, unsafe deserialization, path traversal',
  'resource lifecycle: leaks, unclosed handles, unbounded growth, missing cleanup',
  'API contract: callers broken by the change, type mismatches, nullability',
  'tests: untested branches, tests that pass for the wrong reason, missing negatives',
  'performance: N+1, needless copies, hot-path allocations, quadratic loops',
  'readability: misleading names, dead code, duplicated logic that will drift',
  'data integrity: migrations, partial writes, idempotency, retry safety',
]

const SWEEP_MODES = [
  'by filename and directory names',
  'by symbol: function, class, and type names',
  'by string literals, log messages, and error text',
  'by config keys, env vars, and feature flags',
  'by git history: commits and blame touching the topic',
  'by tests: test names and fixtures that mention the topic',
  'by docs and comments: README, ADRs, inline docs',
]

const DESIGN_ANGLES = ['MVP-first', 'risk-first', 'user-experience-first', 'operability-first', 'performance-first']

const JUDGE_CRITERIA = ['correctness and risk: will it work, what breaks, how it fails', 'simplicity: the least code and fewest moving parts that fully solve it', 'fit: matches the existing code patterns, interfaces, and conventions']
```

Take `REVIEW_LENSES.slice(0, FLEET)` and so on. A finder gets one lens and one
batch of `BATCH` files (section 9), never the whole file list: an agent told to
read 60 files fully skims them. More files means more batches, not more lenses.

## 9. Templates

Shared definitions used below. Every agent prompt in these templates ends with
`${AGENT_RULES}`; keep it there. It is what stops a subagent from reporting to
the main conversation instead of returning to the script. `fan` is the only
way these templates fan out; it keeps the closing parens to one per line.

```js
const FINDINGS = { type: 'object', properties: { findings: { type: 'array', items: { type: 'object', properties: { file: { type: 'string' }, line: { type: 'integer' }, title: { type: 'string' }, detail: { type: 'string' }, severity: { type: 'string', enum: ['high', 'medium', 'low'] } }, required: ['file', 'title', 'detail', 'severity'] } } }, required: ['findings'] }
const VERDICT  = { type: 'object', properties: { refuted: { type: 'boolean' }, reason: { type: 'string' } }, required: ['refuted', 'reason'] }
const LEVEL    = { type: 'string', enum: ['high', 'medium', 'low'] }
const CHECK    = { type: 'object', properties: { real: { type: 'boolean' }, reproducible: { type: 'boolean' }, impact: LEVEL, confidence: LEVEL, reason: { type: 'string' } }, required: ['real', 'reproducible', 'impact', 'confidence', 'reason'] }
const MERGED   = { type: 'object', properties: { findings: { type: 'array', items: { type: 'object', properties: { file: { type: 'string' }, line: { type: 'integer' }, title: { type: 'string' }, detail: { type: 'string' }, severity: LEVEL, lenses: { type: 'array', items: { type: 'string' } } }, required: ['file', 'title', 'detail', 'severity', 'lenses'] } } }, required: ['findings'] }
const MERGE_ASK = 'Merge these review findings. Group findings that describe the same defect: same root cause, even when worded differently or reported a few lines apart. Distinct defects on nearby lines stay separate. Return one finding per group with the clearest title, the most complete detail, the highest severity in the group, and every lens that reported it in lenses. Drop a finding only when it duplicates another or is already in the known list.'
const VERIFY_ASK = 'Verify this finding. Read the code yourself. Answer three questions: real, is the claim actually true in this code; reproducible, can it be triggered with a concrete input; impact, how much it matters in practice. A defect that is hard to reproduce or low in impact is still real; only set real=false when the claim is wrong. Set confidence=low when the code does not settle it, instead of guessing.'
const SCORE    = { type: 'object', properties: { scores: { type: 'array', items: { type: 'object', properties: { index: { type: 'integer' }, score: { type: 'number' }, why: { type: 'string' } }, required: ['index', 'score'] } } }, required: ['scores'] }
const BUILD    = { type: 'object', properties: { applied: { type: 'boolean' }, passed: { type: 'boolean' }, commands: { type: 'array', items: { type: 'string' } }, failures: { type: 'array', items: { type: 'object', properties: { file: { type: 'string' }, error: { type: 'string' } }, required: ['file', 'error'] } } }, required: ['applied', 'passed', 'commands', 'failures'] }
const INTEGRATE_ASK = 'Apply every diff below to this checkout with git apply, in order. Do not commit. Then run the project build and the listed tests; if none are listed, find and run the standard build and test commands. Report every command you ran. Attribute each failure to the file whose change caused it, with the error text. passed=true only when every diff applied and every command succeeded.'
const AGENT_RULES = 'Your final text is your return value and the script collects it. Do not call SendMessage or ListAgents; nothing needs to reach the main conversation. Put everything the script needs in this response.'
// fan(items, fn): run fn(item, index) over every item concurrently, drop nulls.
const fan = async (items, fn) => (await parallel(items.map((x, i) => () => fn(x, i)))).filter(Boolean)
// chunk(xs, n): split a work list into batches of n. Finders get one batch each.
const BATCH = 6
const chunk = (xs, n) => xs.length ? [xs.slice(0, n), ...chunk(xs.slice(n), n)] : []
// verifyAll(findings, verify, cap): one Opus check per finding; then, with every verdict
// in hand, Fable re-checks the `cap` candidates that matter most (failed or unsure Opus
// verdicts and high-severity findings, ranked by severity then confidence). Impact
// re-grades severity and never drops a real defect. A finding nobody could check is
// kept as unsettled, not dropped.
const RANK = { high: 0, medium: 1, low: 2 }
const verifyAll = async (findings, verify, cap) => {
  const checked = await fan(findings, async f => ({ f, c: await verify(f, MODEL_HIGH, 'verify') }))
  const needs = x => !x.c || x.c.confidence === 'low' || x.f.severity === 'high'
  const order = x => RANK[x.f.severity] * 3 + (x.c ? 2 - RANK[x.c.confidence] : 0)
  const picked = new Set(checked.filter(needs).sort((a, b) => order(a) - order(b)).slice(0, cap))
  const final = await fan(checked, async x => picked.has(x) ? { f: x.f, c: (await verify(x.f, MODEL_TOP, 'escalate')) ?? x.c, escalated: true } : x)
  return final.map(({ f, c, escalated = false }) => c ? { ...f, severity: c.impact, check: c, escalated, unsettled: c.confidence === 'low', survives: c.real } : { ...f, check: null, escalated, unsettled: true, survives: true })
}
// judgeDesigns(proposals, about, phase): one Fable judge per JUDGE_CRITERIA entry, each
// shown the proposals in a different rotation so position bias does not pick the
// winner. A proposal's total averages only the scores judges actually gave it.
// Returns null when no judge returned scores, so the caller stops instead of
// silently picking proposal #0.
const judgeDesigns = async (proposals, about, phase) => {
  const view = k => proposals.map((_, i) => (i + k) % proposals.length).map(i => '--- #' + i + '\n' + proposals[i]).join('\n')
  const score = (c, k) => agent(`Judge these designs for: ${about}\nScore each 0-10 on ONE criterion only: ${c}. Refer to each by its # number.\n${view(k)}\n${AGENT_RULES}`, { label: `judge:${c.split(':')[0]}`, phase, schema: SCORE, model: MODEL_TOP })
  const judged = await fan(JUDGE_CRITERIA, score)
  if (!judged.length) return null
  const given = i => judged.map(j => j.scores.find(x => x.index === i)?.score).filter(x => typeof x === 'number')
  const avg = xs => xs.length ? xs.reduce((a, b) => a + b, 0) / xs.length : -1
  const totals = proposals.map((_, i) => avg(given(i)))
  return { totals, best: totals.indexOf(Math.max(...totals)), judges: judged.length }
}
```

Each template below lifts every `agent()` call into a named one-line function,
then fans out or pipelines over the names. Keep that shape when adapting them.

### 9a. Review (find by lens, merge, verify once, escalate, synthesize)

```js
export const meta = { name: 'review', description: 'Multi-lens review with adversarial verification', phases: [{ title: 'Find' }, { title: 'Merge' }, { title: 'Verify' }, { title: 'Escalate' }, { title: 'Synthesize' }] }
const MODEL_CHEAP = 'haiku', MODEL_MID = 'sonnet', MODEL_HIGH = 'opus', MODEL_TOP = 'fable'
const REVIEW_LENSES = [/* paste from section 8 */]
const FINDINGS = /* section 9 */, MERGED = /* section 9 */, CHECK = /* section 9 */, MERGE_ASK = /* section 9 */, VERIFY_ASK = /* section 9 */, AGENT_RULES = /* section 9 */
const fan = /* section 9 */, BATCH = /* section 9 */, chunk = /* section 9 */, RANK = /* section 9 */, verifyAll = /* section 9 */

const B = budget.total || 0
const files = args.files
const clamp = (n, lo, hi) => Math.max(lo, Math.min(hi, n))
// One lens per file, floored at 2 and capped by the lens list; a +Nk budget raises the cap.
const CAP = B ? Math.max(REVIEW_LENSES.length, Math.floor(B / 100_000)) : REVIEW_LENSES.length
const FLEET = clamp(files.length, 2, CAP)
// Finders = lenses x batches. Past FINDER_CAP, trailing lenses are dropped, never files.
const batches = chunk(files, BATCH)
const FINDER_CAP = B ? Math.max(60, Math.floor(B / 25_000)) : 60
const lensN = Math.max(1, Math.min(FLEET, Math.floor(FINDER_CAP / batches.length)))
const dropped = REVIEW_LENSES.slice(lensN, FLEET).map(l => l.split(':')[0]).join(', ')
if (dropped) log(`finder cap ${FINDER_CAP}: dropped lenses ${dropped}`)
const jobs = REVIEW_LENSES.slice(0, lensN).flatMap(lens => batches.map((batch, bi) => ({ lens, batch, bi })))
log(`review: ${files.length} files in ${batches.length} batches, ${lensN} lenses, ${jobs.length} finders`)

// Fable re-checks are capped; a +Nk budget raises the cap.
const ESCALATE_CAP = B ? Math.max(10, Math.floor(B / 50_000)) : 10

const find = j => agent(`Review these files through ONE lens only: ${j.lens}.\nFiles: ${j.batch.join(', ')}\nRead each file fully. Report only concrete defects with file and line.\n${AGENT_RULES}`, { label: `find:${j.lens.split(':')[0]}:${j.bi}`, phase: 'Find', schema: FINDINGS, model: MODEL_MID }).then(r => r && r.findings.map(f => ({ ...f, lens: j.lens.split(':')[0], bi: j.bi })))
const merge = (raw, known, bi) => agent(`${MERGE_ASK}\nKnown:\n${known}\nFindings:\n${JSON.stringify(raw)}\n${AGENT_RULES}`, { label: `merge:${bi}`, phase: 'Merge', schema: MERGED, model: MODEL_MID })
// One merge per batch: duplicates come from different lenses reading the same files.
const mergeBatch = async (raw, bi, known) => {
  const group = raw.filter(f => f.bi === bi)
  if (!group.length || (group.length < 2 && known === 'none')) return group
  return (await merge(group, known, bi))?.findings ?? group
}
const verify = (f, model, tag) => agent(`${VERIFY_ASK}\n${JSON.stringify(f)}\n${AGENT_RULES}`, { label: `${tag}:${f.file}:${f.line ?? 0}`, phase: tag === 'escalate' ? 'Escalate' : 'Verify', schema: CHECK, model })

// Barrier: merging needs every finder's output at once (section 6).
const raw = (await fan(jobs, find)).flat()
const merged = (await fan(batches, (_, bi) => mergeBatch(raw, bi, 'none'))).flat()
const verified = await verifyAll(merged, verify, ESCALATE_CAP)
const confirmed = verified.filter(f => f.survives)
log(`${raw.length} raw, ${merged.length} merged, ${confirmed.length} confirmed`)
const report = await agent(`Write the review report. Most severe first. Each item: file:line, what is wrong, why it matters, suggested fix. List items with unsettled=true separately as needing a human look.\n${JSON.stringify(confirmed, null, 2)}\n${AGENT_RULES}`, { phase: 'Synthesize', model: MODEL_TOP })
return { confirmed, report }
```

Call with `args: { files: [...] }`. Find, merge and verify are barriers on purpose:
merging needs every finding at once, and ranking escalations needs every Opus
verdict at once, so the Fable cap goes to the most severe findings, not the
earliest. If a merge agent fails, that batch's raw findings are verified unmerged.

### 9b. Understand (one reader per module, merge)

```js
export const meta = { name: 'understand', description: 'Map every module in parallel, then merge', phases: [{ title: 'Read' }, { title: 'Merge' }] }
const MODEL_MID = 'sonnet', MODEL_TOP = 'fable'
const AGENT_RULES = /* section 9 */, fan = /* section 9 */
const MAP = { type: 'object', properties: { module: { type: 'string' }, purpose: { type: 'string' }, entrypoints: { type: 'array', items: { type: 'string' } }, dependsOn: { type: 'array', items: { type: 'string' } }, risks: { type: 'array', items: { type: 'string' } } }, required: ['module', 'purpose'] }
log(`understand: ${args.modules.length} modules`)
const read = m => agent(`Read every file under ${m}. Describe purpose, entrypoints, dependencies, and risks. Facts only.\n${AGENT_RULES}`, { label: `read:${m}`, phase: 'Read', schema: MAP, model: MODEL_MID })
const maps = await fan(args.modules, read)
const merged = await agent(`Merge into one architecture overview with a dependency list and the top risks:\n${JSON.stringify(maps)}\n${AGENT_RULES}`, { phase: 'Merge', model: MODEL_TOP })
return { maps, merged }
```

Call with `args: { modules: [...] }`: one reader per module or package the task
touches. A two-module job gets two readers, not six.

### 9c. Design (judge panel)

```js
export const meta = { name: 'design-panel', description: 'Independent designs from several angles, judged, synthesized', phases: [{ title: 'Propose' }, { title: 'Judge' }, { title: 'Synthesize' }] }
const MODEL_HIGH = 'opus', MODEL_TOP = 'fable'
const DESIGN_ANGLES = [/* section 8 */]
const JUDGE_CRITERIA = [/* section 8 */]
const SCORE = /* section 9 */, AGENT_RULES = /* section 9 */, fan = /* section 9 */, judgeDesigns = /* section 9 */
const B = budget.total || 0
// 2 proposals for a small design, up to the angle list; a +Nk budget adds rows.
const N = Math.max(2, Math.min(DESIGN_ANGLES.length, 2 + Math.floor(B / 150_000)))
const propose = a => agent(`Problem: ${args.problem}\nContext: ${args.context}\nDesign a solution from the ${a} angle. Return the design as text with tradeoffs.\n${AGENT_RULES}`, { label: `propose:${a}`, phase: 'Propose', model: MODEL_HIGH })
const proposals = await fan(DESIGN_ANGLES.slice(0, N), propose)
if (!proposals.length) return { stopped: 'every proposer failed' }
const ranked = await judgeDesigns(proposals, args.problem, 'Judge')
if (!ranked) return { proposals, stopped: 'every judge failed' }
const { totals, best } = ranked
log(`winner #${best} by ${ranked.judges} judges, totals ${JSON.stringify(totals)}`)
const others = proposals.filter((_, i) => i !== best).join('\n---\n')
const final = await agent(`Synthesize the final design from the winner, grafting the best ideas from the others. End with an ordered implementation plan listing files to change.\nWinner:\n${proposals[best]}\nOthers:\n${others}\n${AGENT_RULES}`, { phase: 'Synthesize', model: MODEL_TOP })
return { final, totals }
```

Call with `args: { problem, context }` where context is the merged output of 9b.

### 9d. Research (sweep, read all hits, critique, synthesize)

```js
export const meta = { name: 'research', description: 'Multi-mode sweep, read every hit, critique gaps, answer', phases: [{ title: 'Sweep' }, { title: 'Read' }, { title: 'Critique' }] }
const MODEL_CHEAP = 'haiku', MODEL_MID = 'sonnet', MODEL_TOP = 'fable'
const SWEEP_MODES = [/* section 8 */]
const AGENT_RULES = /* section 9 */, fan = /* section 9 */
const HITS = { type: 'object', properties: { hits: { type: 'array', items: { type: 'string' } } }, required: ['hits'] }
// 40 reads by default; a +Nk budget raises the cap.
const CAP = budget.total ? Math.max(40, Math.floor(budget.total / 25_000)) : 40
const sweep = m => agent(`Search ${m} for anything relevant to: ${args.question}. Return file paths only.\n${AGENT_RULES}`, { label: `sweep:${m.slice(3, 20)}`, phase: 'Sweep', schema: HITS, model: MODEL_CHEAP })
const sweeps = await fan(SWEEP_MODES, sweep)
const list = [...new Set(sweeps.flatMap(r => r.hits))]
if (list.length > CAP) log(`capping reads at ${CAP} of ${list.length}; dropped: ${list.slice(CAP).join(', ')}`)
const read = f => agent(`Read ${f} in full. Extract everything relevant to: ${args.question}. Facts only, cite line numbers.\n${AGENT_RULES}`, { label: `read:${f}`, phase: 'Read', model: MODEL_MID })
const notes = await fan(list.slice(0, CAP), read)
const joined = notes.join('\n---\n')
const critique = await agent(`Question: ${args.question}\nNotes:\n${joined}\n\nFirst list what is missing: unverified claims, sources not read, search modes that would find more. Then answer the question as completely as the notes allow.\n${AGENT_RULES}`, { phase: 'Critique', model: MODEL_TOP })
return { files: list, answer: critique }
```

If the critique names gaps, close them inside the same script: give the critique
a schema with a `gaps: string[]` field and loop, running another sweep and read
round over the gaps until the list is empty or three rounds have run. Do not end
the workflow and relaunch for the gaps, and do not read them inline.

### 9e. Implement / migrate (one agent per file, verified)

```js
export const meta = { name: 'implement', description: 'Apply a change per file in isolated worktrees, verify each, build them together', phases: [{ title: 'Transform' }, { title: 'Verify' }, { title: 'Integrate' }] }
const MODEL_MID = 'sonnet', MODEL_HIGH = 'opus'
const AGENT_RULES = /* section 9 */, VERDICT = /* section 9 */, BUILD = /* section 9 */, INTEGRATE_ASK = /* section 9 */
const RESULT = { type: 'object', properties: { changed: { type: 'boolean' }, diff: { type: 'string' }, notes: { type: 'string' } }, required: ['changed'] }
log(`implement: ${args.files.length} files`)
const tx = f => agent(`Task: ${args.task}\nApply it to ${f} only. Do not commit. Return the unified diff.\n${AGENT_RULES}`, { label: `tx:${f}`, phase: 'Transform', schema: RESULT, isolation: 'worktree', model: MODEL_MID })
const check = (f, r) => agent(`Task was: ${args.task}\nCheck this diff for ${f}: does it compile, preserve behavior, and fully do the task? Refute if any answer is no.\n${r.diff}\n${AGENT_RULES}`, { label: `verify:${f}`, phase: 'Verify', schema: VERDICT, model: MODEL_HIGH })
const verify = async (r, f) => {
  if (!r?.changed) return null
  const verdict = await check(f, r)
  return { file: f, diff: r.diff, verdict }
}
const out = await pipeline(args.files, tx, verify)
const results = out.filter(Boolean)
log(`${results.length} changed, ${results.filter(r => r.verdict?.refuted).length} refuted`)
// The diff checker only reads one file's diff; only a real build of all of them proves they fit.
const passing = results.filter(r => r.verdict && !r.verdict.refuted)
const diffs = passing.map(r => '--- ' + r.file + '\n' + r.diff).join('\n')
const tests = (args.tests ?? []).join(', ') || 'none listed'
const integrate = () => agent(`${INTEGRATE_ASK}\nTests: ${tests}\n${diffs}\n${AGENT_RULES}`, { label: 'integrate', phase: 'Integrate', schema: BUILD, isolation: 'worktree', model: MODEL_MID })
const build = passing.length ? await integrate() : null
log(`integrate: ${build ? (build.passed ? 'passed' : build.failures.length + ' failures') : 'not run'}`)
return { results, build }
```

Call with `args: { files: [...], task: "...", tests: [...] }`; `tests` is optional.
Worktree isolation is required here because files are edited concurrently.
Applying the surviving diffs is the one inline step allowed afterwards, and only
when `build.passed`. Refuted files are retried inside the script,
not in a second workflow: add a stage that re-runs the transform with the
verdict's reason appended to the prompt, then verifies again, as in 9g.

### 9f. Discovery loop (until dry)

```js
// batches, jobs, merge, mergeBatch, verify, ESCALATE_CAP as defined in 9a.
const seen = [], confirmed = []
const knownIn = b => seen.filter(f => b.includes(f.file)).map(f => f.file + ':' + (f.line ?? 0) + ' ' + f.title).join('\n') || 'none'
let dry = 0, round = 0, escalations = ESCALATE_CAP   // shared across rounds
while (dry < 2 && round < 8) {
  round++
  const find = j => agent(`Round ${round}. Lens: ${j.lens}. Find defects in ${j.batch.join(', ')} not in this list:\n${knownIn(j.batch)}\n${AGENT_RULES}`, { label: `find:${round}:${j.lens.split(':')[0]}:${j.bi}`, phase: 'Find', schema: FINDINGS, model: MODEL_MID }).then(r => r && r.findings.map(f => ({ ...f, lens: j.lens.split(':')[0], bi: j.bi })))
  const raw = (await fan(jobs, find)).flat()
  const fresh = (await fan(batches, (b, bi) => mergeBatch(raw, bi, knownIn(b)))).flat()
  if (!fresh.length) { dry++; continue }
  dry = 0
  seen.push(...fresh)
  const judged = await verifyAll(fresh, verify, escalations)
  escalations -= judged.filter(j => j.escalated).length
  confirmed.push(...judged.filter(j => j.survives))
  log(`round ${round}: ${raw.length} raw, ${fresh.length} new, ${confirmed.length} confirmed`)
}
```

Each batch's merge dedups the round against `seen` (every earlier finding, confirmed
or not), so rejected findings and rewordings of known ones do not come back.

### 9g. End-to-end job (understand, design, implement, review, report)

The default for any heavy job. Each phase sizes itself from the list the previous
phase produced, so counts differ by phase as section 2 requires.

```js
export const meta = { name: 'job', description: 'Understand, design, implement, review and report one job in a single run', phases: [{ title: 'Understand' }, { title: 'Design' }, { title: 'Implement' }, { title: 'Integrate' }, { title: 'Review' }, { title: 'Report' }] }
const MODEL_CHEAP = 'haiku', MODEL_MID = 'sonnet', MODEL_HIGH = 'opus', MODEL_TOP = 'fable'
const REVIEW_LENSES = [/* section 8 */], DESIGN_ANGLES = [/* section 8 */], JUDGE_CRITERIA = [/* section 8 */]
const FINDINGS = /* section 9 */, VERDICT = /* section 9 */, MERGED = /* section 9 */, CHECK = /* section 9 */, SCORE = /* section 9 */, BUILD = /* section 9 */
const MERGE_ASK = /* section 9 */, VERIFY_ASK = /* section 9 */, INTEGRATE_ASK = /* section 9 */, AGENT_RULES = /* section 9 */
const fan = /* section 9 */, BATCH = /* section 9 */, chunk = /* section 9 */, RANK = /* section 9 */, verifyAll = /* section 9 */, judgeDesigns = /* section 9 */
const MAP = { type: 'object', properties: { module: { type: 'string' }, purpose: { type: 'string' }, files: { type: 'array', items: { type: 'string' } }, risks: { type: 'array', items: { type: 'string' } } }, required: ['module', 'purpose', 'files'] }
const OVERVIEW = { type: 'object', properties: { overview: { type: 'string' }, files: { type: 'array', items: { type: 'string' } } }, required: ['overview', 'files'] }
const PLAN = { type: 'object', properties: { design: { type: 'string' }, files: { type: 'array', items: { type: 'object', properties: { path: { type: 'string' }, change: { type: 'string' } }, required: ['path', 'change'] } }, tests: { type: 'array', items: { type: 'string' } } }, required: ['design', 'files'] }
const RESULT = { type: 'object', properties: { changed: { type: 'boolean' }, diff: { type: 'string' }, notes: { type: 'string' } }, required: ['changed'] }
const B = budget.total || 0
const low = () => B && budget.remaining() < 60_000
const task = args.task

// Understand: one reader per module the task names.
log(`understand: ${args.modules.length} modules`)
const read = m => agent(`Task context: ${task}\nRead every file under ${m}. Describe purpose and risks, and list the files that this task would plausibly touch. Facts only.\n${AGENT_RULES}`, { label: `read:${m}`, phase: 'Understand', schema: MAP, model: MODEL_MID })
const maps = await fan(args.modules, read)
const mapsJson = JSON.stringify(maps)
const understood = await agent(`Task: ${task}\nMerge these module maps into one overview and the deduplicated list of files the task touches:\n${mapsJson}\n${AGENT_RULES}`, { phase: 'Understand', schema: OVERVIEW, model: MODEL_TOP })
if (!understood) return { stopped: 'understand returned nothing', maps }

// Design: proposals from distinct angles, judged, synthesized into a plan.
const N = Math.max(2, Math.min(DESIGN_ANGLES.length, 2 + Math.floor(B / 150_000)))
const involved = understood.files.join(', ')
const propose = a => agent(`Task: ${task}\nCodebase overview:\n${understood.overview}\nFiles involved: ${involved}\nDesign a solution from the ${a} angle, with tradeoffs.\n${AGENT_RULES}`, { label: `propose:${a}`, phase: 'Design', model: MODEL_HIGH })
const proposals = await fan(DESIGN_ANGLES.slice(0, N), propose)
if (!proposals.length) return { understood, stopped: 'every proposer failed' }
const ranked = await judgeDesigns(proposals, task, 'Design')
if (!ranked) return { understood, proposals, stopped: 'every judge failed' }
const { totals, best } = ranked
log(`design: winner #${best} by ${ranked.judges} judges, totals ${JSON.stringify(totals)}`)
const others = proposals.filter((_, i) => i !== best).join('\n---\n')
const plan = await agent(`Task: ${task}\nSynthesize the final design from the winner, grafting the best ideas from the others. Return the design, the exact files to change with the change for each, and the tests to run.\nWinner:\n${proposals[best]}\nOthers:\n${others}\n${AGENT_RULES}`, { phase: 'Design', schema: PLAN, model: MODEL_TOP })
if (!plan?.files?.length) return { understood, proposals, totals, stopped: 'design produced no file list' }
if (low()) { log('budget low after design; stopping before implement'); return { understood, plan, stopped: 'budget' } }

// Implement: one transformer per planned file, verified, retried once with the verdict.
log(`implement: ${plan.files.length} files`)
const tx = (f, extra) => agent(`Task: ${task}\nDesign:\n${plan.design}\nApply this change to ${f.path} only: ${f.change}${extra}\nDo not commit. Return the unified diff.\n${AGENT_RULES}`, { label: `tx:${f.path}`, phase: 'Implement', schema: RESULT, isolation: 'worktree', model: MODEL_MID })
const check = (f, r) => agent(`Task: ${task}\nIntended change for ${f.path}: ${f.change}\nDoes this diff compile, preserve unrelated behavior, and fully make the intended change? Refute if any answer is no.\n${r.diff}\n${AGENT_RULES}`, { label: `verify:${f.path}`, phase: 'Implement', schema: VERDICT, model: MODEL_HIGH })
const verifyWithRetry = async (r, f) => {
  if (!r?.changed) return null
  let v = await check(f, r)
  if (v && !v.refuted) return { file: f.path, diff: r.diff, verdict: v, retried: false }
  const reason = v?.reason ?? 'unknown'
  const r2 = await tx(f, `\nA previous attempt was refuted for this reason: ${reason}. Fix that.`)
  if (!r2?.changed) return { file: f.path, diff: r.diff, verdict: v, retried: true }
  v = await check(f, r2)
  return { file: f.path, diff: r2.diff, verdict: v, retried: true }
}
const implemented = (await pipeline(plan.files, f => tx(f, ''), verifyWithRetry)).filter(Boolean)
const accepted = implemented.filter(x => x.verdict && !x.verdict.refuted)
const rejected = implemented.filter(x => !x.verdict || x.verdict.refuted)
log(`implement: ${accepted.length} accepted, ${rejected.length} rejected after retry`)

// Integrate: every accepted diff applied together in one worktree, built and tested.
// Files the build blames are re-transformed once with the error and the other diffs,
// then the whole set is rebuilt; the rebuild is the check for those retries.
const diffsOf = set => set.map(a => '--- ' + a.file + '\n' + a.diff).join('\n')
const tests = (plan.tests ?? []).join(', ') || 'none listed'
const integrate = n => agent(`${INTEGRATE_ASK}\nTests: ${tests}\n${diffsOf(accepted)}\n${AGENT_RULES}`, { label: `integrate:${n}`, phase: 'Integrate', schema: BUILD, isolation: 'worktree', model: MODEL_MID })
let build = accepted.length ? await integrate(1) : null
const blamed = new Set((build?.failures ?? []).map(x => x.file))
const refix = async a => {
  const why = build.failures.filter(x => x.file === a.file).map(x => x.error).join('; ')
  const others = diffsOf(accepted.filter(o => o.file !== a.file))
  const r = await tx(plan.files.find(p => p.path === a.file), `\nThe combined build failed on this file: ${why}\nThe other files change as follows:\n${others}\nFix this file only.`)
  return r?.changed ? { ...a, diff: r.diff, retried: true } : a
}
if (build && !build.passed && accepted.some(a => blamed.has(a.file))) {
  const fixed = await fan(accepted, async a => blamed.has(a.file) ? refix(a) : a)
  accepted.splice(0, accepted.length, ...fixed)
  build = await integrate(2)
}
log(`integrate: ${build ? (build.passed ? 'passed' : build.failures.length + ' failures') : 'not run'}`)

// Review: lenses over batches of the accepted diffs, merged, verified once, escalated as in 9a.
const diffFor = file => diffsOf(accepted.filter(a => a.file === file)) || diffsOf(accepted)
const batches = chunk(accepted, BATCH)
const LENSES = REVIEW_LENSES.slice(0, Math.max(2, Math.min(REVIEW_LENSES.length, accepted.length)))
const jobs = LENSES.flatMap(lens => batches.map((batch, bi) => ({ lens, batch, bi })))
const find = j => agent(`Review these diffs through ONE lens only: ${j.lens}.\nTask: ${task}\n${diffsOf(j.batch)}\nReport only concrete defects with file and line.\n${AGENT_RULES}`, { label: `find:${j.lens.split(':')[0]}:${j.bi}`, phase: 'Review', schema: FINDINGS, model: MODEL_MID }).then(r => r && r.findings.map(f => ({ ...f, lens: j.lens.split(':')[0], bi: j.bi })))
const merge = (group, bi) => agent(`${MERGE_ASK}\nKnown:\nnone\nFindings:\n${JSON.stringify(group)}\n${AGENT_RULES}`, { label: `merge:${bi}`, phase: 'Review', schema: MERGED, model: MODEL_MID })
const mergeBatch = async (raw, bi) => {
  const group = raw.filter(f => f.bi === bi)
  return group.length < 2 ? group : (await merge(group, bi))?.findings ?? group
}
const verify = (f, model, tag) => agent(`${VERIFY_ASK}\n${JSON.stringify(f)}\nDiff:\n${diffFor(f.file)}\n${AGENT_RULES}`, { label: `${tag}:${f.file}:${f.line ?? 0}`, phase: 'Review', schema: CHECK, model })
const ESCALATE_CAP = B ? Math.max(10, Math.floor(B / 50_000)) : 10
const raw = (await fan(jobs, find)).flat()
const merged = (await fan(batches, (_, bi) => mergeBatch(raw, bi))).flat()
const confirmed = (await verifyAll(merged, verify, ESCALATE_CAP)).filter(f => f.survives)
log(`review: ${raw.length} raw, ${merged.length} merged, ${confirmed.length} confirmed`)

// Report: one top-tier agent writes what to apply and what is left.
const rejectedJson = JSON.stringify(rejected.map(r => ({ file: r.file, reason: r.verdict?.reason })))
const confirmedJson = JSON.stringify(confirmed, null, 2)
const buildJson = JSON.stringify(build)
const report = await agent(`Write the final report for: ${task}\nDesign:\n${plan.design}\nAccepted diffs: ${accepted.map(a => a.file).join(', ')}\nRejected after retry: ${rejectedJson}\nBuild and tests over all accepted diffs, null if not run:\n${buildJson}\nConfirmed review findings:\n${confirmedJson}\nState what to apply, what to fix first, and what was left out and why. If the build did not pass, say so first.\n${AGENT_RULES}`, { phase: 'Report', model: MODEL_TOP })
return { understood, plan, totals, accepted, rejected, build, confirmed, report }
```

Call with `args: { task: "...", modules: [...] }` where `modules` is the scouted
list of directories the task touches. The dispatcher's only inline step after
the result is applying the accepted diffs, and only when `build.passed`. If the report names rejected files or
confirmed findings worth fixing, that is a new, smaller job: one more workflow
over those files, not inline edits.

## 10. Writing agent prompts

- First sentence is the task, last sentence is the return shape.
- End every prompt with `AGENT_RULES`. Without it a subagent may report to the
  main conversation instead of returning, which wakes the dispatcher and leaves
  the script's structured results stale. Never write a prompt that asks an agent
  to notify, report to, or message main.
- Inline every fact the agent needs. It does not see this conversation.
- Diff checkers (VERDICT): say "Refute if any answer is no." Finding verifiers
  (CHECK): use `VERIFY_ASK`, which asks for confidence=low rather than a default
  verdict, so uncertainty escalates instead of silently dropping the finding.
  Readers: say "Facts only."
- Never tell an agent to read CLAUDE.md. It already has it.
- With a schema, do not also ask for prose.
- Prompt text contains no backticks and no nested `${`...`}`. Name files bare;
  precompute joined lists into a `const` and interpolate the name (section 5).

## 11. Pre-flight checklist

1. Opt-in present (section 0)?
2. Sizing derived from the step's own work list, per section 2, with the budget only raising the cap? Counts differ between steps because the work does?
3. Does each step produce something the next one consumes, and is every load-bearing claim checked by something independent? Code changes are checked by building and testing them together, not only by reading diffs.
4. Does the script run EVERY phase of the job, so one launch and one wait cover it? A second launch you planned for a later phase belongs inside this script.
5. Is there any work you planned to do inline afterwards that should be in the script?
6. `meta` first, literal, with name and description; phase titles match?
7. No `Date.now`, `Math.random`, `new Date()`, TypeScript, imports?
8. Every `parallel` argument is an array of thunks?
9. Every result array `.filter(Boolean)`-ed?
10. Schemas: object root, `required` subset of `properties`?
11. `args` passed as real JSON?
12. Model tier set per stage?
13. Any cap or sampling is `log()`-ed with what was dropped?
14. Does every agent prompt end with `AGENT_RULES`, so no subagent messages main?
15. Will you run `date`, state the expected wall clock with the `runId`
    (section 13), and then end the turn rather than act while it runs?
16. Checked the syntax? Write the exact script you are about to submit to
    `.tmp/wf.js` and run
    `python3 ~/.claude/skills/workflow-cookbook/check-script.py .tmp/wf.js`.
    It parses the script the way the tool does and prints the node error with
    the line number. Fix until it prints `ok`, then submit the same text. One
    Bash call is cheaper than a failed launch and a re-author.

## 12. After the run

- The tool returns immediately with `runId` and `scriptPath`. The result arrives
  later as a task notification. Do not predict it. Until it arrives, section 13
  applies.
- Odd or empty result: Read `<transcriptDir>/journal.jsonl` first.
- To fix: Edit the file at `scriptPath`, TaskStop the old run, then
  `Workflow({ scriptPath, resumeFromRunId })`. Only the changed tail re-runs.
- Relay the outcome in your own words. A further workflow is for a new job, or
  for rejected files and confirmed findings the report names. It is never for a
  phase that should have been in the script. Re-read section 1 before doing
  anything inline.

## 13. Waiting for a run (slow backends)

The Workflow tool returns at once. The run continues in the background and its
result arrives as a `<task-notification>` naming your `runId`, which re-enters
your context on its own. There is nothing for you to do until then. The backend
behind this harness is noticeably slower than the public API, so one agent turn
can take several minutes and a three-stage run of 30 agents routinely takes 30
to 90 minutes. That is normal. Silence is not a hang.

**Ending the turn is the correct action, not giving up.** The harness rule "end
your turn only when the task is complete or you are blocked on input only the
user can provide" is satisfied here: a running workflow is input you cannot
produce yourself. Waiting for it by ending the turn obeys that rule. Continuing
to act instead violates the dispatcher rule in section 1.

At launch, do these three things, then end the turn:

1. Run `date` once. You have no clock; without a recorded start time, "how long
   has it been" is a guess, and guesses on a slow backend run short.
2. Compute the expected wall clock:

   ```
   minutes ≈ stages × ceil(agents_per_stage / 12) × minutes_per_agent
   ```

   Use 3 to 10 for `minutes_per_agent` and the largest stage for
   `agents_per_stage`. Nothing is late until twice that estimate.
3. Write one line to the user containing the `runId`, the start time, and the
   estimate. That line is also your own record: it survives context compaction,
   so a later version of you does not re-launch a run that is still going.

While a run is in flight:

- Do not poll. No repeated reads of `journal.jsonl`, no `/workflows` loops, no
  "checking in" messages, no ScheduleWakeup shorter than 20 minutes.
- Do not TaskStop a run because time has passed. Elapsed time is not evidence of
  failure. The only grounds to stop a run are: the user asks, or the journal
  shows a script error. Budget exhaustion stops the run by itself.
- Do not launch the same script again "in case the first one was lost". Two live
  runs double the cost and both write results.
- Do not launch a second workflow for the same job while the first runs. Its
  phases are already inside the script. A workflow for an unrelated job may run
  alongside it.
- Do not start the work inline while waiting. The run will produce it, and
  anything you do meanwhile is duplicated and fills your context with file
  contents (section 1).
- Do not predict, summarize, or "preliminarily report" a result you do not have.

Not every wake-up is the result. A subagent message, a user message, a cron
firing, or a ScheduleWakeup all re-enter your context while the run continues.
Only a `<task-notification>` that names your `runId` means it finished. On any
other wake-up: handle whatever it was, run `date` to get the real elapsed time,
and end the turn again.

If the user asks whether it is done and it is not: say it is still running, give
elapsed against expected, and end the turn again. If you must check liveness, do
it once with `wc -l` or `tail -n 1` on `journal.jsonl`, never `cat`: the file is
large and belongs in the run's context, not yours. A run is alive if the line
count has grown since you last looked. If it has not grown for longer than twice
the estimate, report that to the user with the last journal line and let them
decide. Do not stop or re-launch on your own.
