# Operator checklist: ultracode on a non-Claude backend

Everything agreed on 2026-10-10, in the order to check when workflows come out
too small or the model drifts back into doing the work in its own context.
Tick each item; most regressions trace to one of the first four.

## A. Harness settings (one-time)

- [x] **Workflow size guideline is unrestricted.** Set via `/config` → "Dynamic
      workflow size" on 2026-10-10. Equivalent persistent key in
      `~/.claude/settings.json`: `"workflowSizeGuideline": "unrestricted"`.
      When the key is in a settings file the `/config` row is hidden; either place
      works. Default is "medium" (under 10 agents), which the model reads as a cap.
- [ ] **Ultracode keyword trigger is on.** Default true. Settings key:
      `"workflowKeywordTriggerEnabled": true`. If someone turned it off, the word
      `ultracode` in a prompt does nothing.
- [ ] **Workflows enabled.** `enableWorkflows` must not be false and
      `disableWorkflows` must not be true in any settings source or env
      (`CLAUDE_CODE_DISABLE_WORKFLOWS`).
- [ ] **Session-wide ultracode (optional).** `"ultracode": true` passed via
      `--settings <file>` turns it on for the whole session instead of per prompt.
      Schema note: it also requests xhigh effort and "requires an xhigh-capable
      model". On a non-Claude backend this may be refused or ignored; if the
      session fails to start with it, fall back to the per-prompt keyword.

## B. Model routing env (one-time, per backend)

- [ ] `ANTHROPIC_BASE_URL` points at the in-house proxy.
- [ ] `ANTHROPIC_AUTH_TOKEN` or `ANTHROPIC_API_KEY` set.
- [ ] Alias remap so cookbook scripts stay portable (names medium confidence,
      verify with `claude --help` and the settings docs):
      `ANTHROPIC_DEFAULT_HAIKU_MODEL`, `ANTHROPIC_DEFAULT_SONNET_MODEL`,
      `ANTHROPIC_DEFAULT_OPUS_MODEL`, `ANTHROPIC_DEFAULT_FABLE_MODEL`,
      `ANTHROPIC_MODEL`, `CLAUDE_CODE_SUBAGENT_MODEL`. The FABLE one is not in
      the env-var reference as of 2026-10-10, so probe it rather than assume.
- [ ] **Top tier resolves.** All four constants are aliases and track their env
      var. The alias table, confirmed 2026-10-10, is: `haiku` → `gpt-6-luna`,
      `sonnet` → `gpt-6.1-sol`, `opus` → `gpt-6.1-sol`, `fable` → `gpt-6-astra`.
      `ANTHROPIC_DEFAULT_FABLE_MODEL` is the one unverified link (absent from the
      env-var reference); probe a request with `"model":"fable"` once. If it does
      not resolve, write `gpt-6-astra` into `MODEL_TOP` in the templates. The
      client-side `behavesAs: "claude-fable-5-1"` label does not route anything.
- [ ] Backend accepts forced `tool_choice` for a named tool. Without it every
      `agent(..., {schema})` returns null. Run the smoke test in BACKEND-NOTES.md.
- [ ] **Haiku alias resolves.** CONFIRMED FAILURE on 2026-10-10: a subagent
      launched with `model: "haiku"` got `422 model not found:
      "claude-haiku-4-5-20251001"` from the proxy. Until the alias is remapped
      (env var above) or the proxy serves that ID, every cookbook stage using
      `MODEL_CHEAP = 'haiku'`, the built-in `claude-code-guide` agent, and any
      hook of type `prompt` or `agent` (which default to Haiku) will fail. The
      `modelPreferences` map in settings.json covers `gpt-6-luna → haiku`
      behaviour but not the reverse lookup from the alias.

## C. Instructions the model sees every turn

- [ ] `~/.claude/skills/workflow-cookbook/SKILL.md` present and listed in `/skills`.
- [ ] `node` on PATH, so `check-script.py` (pre-flight 16) works. Without node
      the checker says so and the model should still submit; it just loses the
      pre-submit parse check.
- [ ] `~/.claude/CLAUDE.md` contains the "Ultracode sizing" block (dispatcher
      rule, work-proportional counts, "large fan-out is safe"). It is gated on the
      `ultracode` keyword or a `+Nk` budget so ordinary turns are unaffected.
- [ ] The model loads `workflow-authoring` then `workflow-cookbook` before writing
      a script. If it skips the cookbook, add "load workflow-cookbook" to the prompt
      once and see whether behaviour changes; if it does, strengthen the skill
      description's trigger words.

## D. Per-prompt habits for heavy jobs

- [ ] Include `ultracode` in the prompt.
- [ ] Include a token budget such as `+500k`. This sets `budget.total`, which the
      cookbook uses to raise the per-step cap. Without a budget it falls back to
      the work-list ceiling only.
- [ ] Describe the whole job, not one phase of it. The model should answer a
      heavy job with ONE workflow whose script runs understand, design, implement,
      review and report (cookbook 9g), handing results between phases internally.
      Phase count still tracks the task, so a small job should come back with few
      phases, but they should be in one script, not one script per turn.
- [ ] After the workflow returns, expect the model to apply accepted diffs and
      relay the report. A further workflow is for rejected files or confirmed
      findings, or a new job. If the model starts reading files itself, say
      "dispatcher rule" and it should re-launch.
- [ ] On a slow backend, expect the model to launch, state an expected duration,
      and end its turn. A long quiet turn is correct. If it instead stops the
      run, re-launches it, or starts working inline before the notification,
      say "section 13, wait for the notification" and it should stand down.

## E. Diagnosing a run that still came out small

| Symptom | Likely cause | Fix |
|---|---|---|
| 2-3 agents, one stage | size guideline still "medium", or cookbook not loaded | A1, C3 |
| One workflow per phase across turns (understand, then design, then implement, then verify) | an older cookbook or CLAUDE.md block mandated a sequence of workflows; the built-in authoring reference also suggests it under ultracode | cookbook section 1 and template 9g now mandate one script for the whole job; confirm the CLAUDE.md ultracode block says the same |
| Right size, but no step checks anything | model skipped the independent-check invariant | quote cookbook section 2 in the prompt once |
| Fixed six-lens review on a one-file change | floors not yet rewritten to be work-proportional in your copy | cookbook section 2, per-step counts |
| All schema agents return null | backend ignores forced tool_choice | B4, or switch templates to JSON-in-text |
| Workflow fine, then model reads 20 files itself | dispatcher rule ignored | activate the guard hook (section F) |
| Script parse error `Unexpected token (N:0)` at a line that starts a new statement such as `phase('Design')` | not TypeScript despite the harness hint: an unclosed `(`/`[`/`{` in the statement above, or a backtick inside prompt text that ended the template literal early | cookbook section 5 shape rules and diagnosis table; templates now use `fan` and one-line named agent calls; have the model run `check-script.py` on the script before submitting (pre-flight 16). To diagnose a failed one, copy the script out of the transcript and run `python3 check-script.py that.js` |
| Script parse error elsewhere | TypeScript syntax, Date.now, non-literal meta | cookbook section 5 |
| Workflow returns empty | read `journal.jsonl` in the transcript dir before re-running | cookbook section 12 |
| Model TaskStops, re-launches, or starts inline work while the run is still going | impatience: the in-house API is slower than the public one (not slow enough to time out), and the harness's "end your turn only when the task is complete" rule reads to the model as "keep acting" | cookbook section 13 resolves that conflict explicitly; put "this may take an hour, end your turn and wait for the notification" in the prompt once |
| Model treats a subagent message or user message as the result and starts the next phase | wake-up mistaken for the task notification | cookbook section 13: only a task notification naming the runId is the result |

## F. Dispatcher guard hook (staged, NOT active)

Observed 2026-10-10 in the vips run: the workflow's 14 subagents made 16
`SendMessage` calls, all `to: "main"`, none of them cross-session (no
`<cross-session-message>` markers reached the transcript). Each one wakes the
main loop. Worse, one verifier sent a *retraction* of a finding by SendMessage,
which never reached the script's structured results, so the workflow could
report as confirmed something its own agent had retracted. Two fixes applied:
every template prompt now ends with `AGENT_RULES`, which forbids SendMessage and
states the return path; and the hook below denies subagent SendMessage outright.

Files live in `~/.claude/hooks/ultracode-guard/`: `arm.sh` (UserPromptSubmit,
arms on `ultracode` or `+Nk`, disarms on `ultracode off`), `guard.sh`
(PreToolUse, 3 reads / 1 edit per turn in the main context, subagents exempt via
`agent_id` except for `SendMessage`), `settings-snippet.json` (block to merge),
`test.sh` (self-test), `README.md` (activation, deactivation, caveats). Run
`test.sh` first, merge the snippet, open `/hooks` once. Activate only if section
D4 keeps failing after A to C are confirmed, because a hook that denies Read in
the main context is blunt: it also blocks legitimate scouting past the limit.

## G. If prompt-level fixes are not enough

The remaining gap is disposition, which only training changes. The cookbook
templates are a seed for a small supervised set of (task, work list) → script
pairs. Collect the scripts that worked from the session transcript directories
(each Workflow call persists its script) and use those as positives.

## Quality-preserving top tier

The cookbook uses the top tier for final synthesis, design judging, and decisive
verification. Keep cheaper tiers for routine work, not for decisions whose
mistakes determine the final result. For disputed findings, escalate to a
top-tier verifier.

Routing note (2026-10-10): all four cookbook constants are aliases that track
their env vars, so re-pointing a tier is one settings change and no script edit.
The proxy serves `gpt-6-luna`, `gpt-6.1-sol` and `gpt-6-astra`; the aliases map to
them as in checklist section B. `ANTHROPIC_DEFAULT_FABLE_MODEL` remains the one
unverified link. A `behavesAs` profile changes client handling, not the underlying
model's quality. Do not silently downgrade the top tier if the endpoint is
unavailable.
