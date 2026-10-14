# Workflow Cookbook

A Claude Code skill that helps non-Claude models use Claude Code's dynamic `Workflow` tool effectively.

The cookbook provides workflow sizing guidance, orchestration patterns, and reusable script templates. It is intended for setups that run other models through a compatible Claude Code harness or proxy. It supplies instructions and examples, not a standalone workflow engine.

## What it helps with

- Size each phase from the actual work list and available token budget rather than choosing an arbitrary agent count.
- Keep a heavy job in one workflow, passing results through production, checking, and synthesis instead of stopping after each phase.
- Choose model tiers for individual stages, reserving stronger models for judgment and decisive verification.
- Adapt templates for reviews, codebase exploration, design, research, implementation, and end-to-end tasks.
- Check script syntax before submission, wait for completion notifications, and resume failed runs without repeating completed work.

## Requirements

- A Claude Code harness that exposes the dynamic `Workflow` tool, with workflows enabled. Installing this skill does **not** install or enable that runtime.
- Access to the built-in `workflow-authoring` skill. It is the API reference; this cookbook adds sizing guidance and templates. Load the reference first, then the cookbook, before authoring a workflow script.
- For non-Claude models, a compatible backend or proxy that supports the harness's tool-calling protocol. Schema-based agents also depend on forced named-tool selection.
- Python 3 and Node.js on `PATH` if you want to use the included syntax checker.

Check tool availability and model routing in your own environment before launching a large run. The operator documents describe a particular setup, not guaranteed support across every Claude Code version or backend.

## Installation

Install as a user-level Claude Code skill:

```sh
mkdir -p ~/.claude/skills
git clone https://github.com/happyaron/workflow-cookbook.git ~/.claude/skills/workflow-cookbook
```

Start a new Claude Code session and check that `workflow-cookbook` appears in `/skills`.

For harness configuration and persistent dispatcher instructions, see the [operator checklist](OPERATOR-CHECKLIST.md). Its references to a separate guard hook describe operator-local files; that hook is not included in this repository.

## Usage

Explicitly request a workflow for the task you want to delegate. For example:

```text
Load workflow-authoring, then workflow-cookbook. Use a workflow to review
src/ for correctness bugs, independently verify findings, and report the results.
```

If your harness supports the `ultracode` keyword and token-budget shorthand, you can use prompts such as:

```text
ultracode +500k review src/ for correctness bugs and verify each finding.
```

```text
ultracode implement the requested refactor across src/ in one end-to-end
workflow, including exploration, design, implementation, review, and reporting.
```

The cookbook directs the parent model to coordinate the work rather than do the substantive implementation or review inline. Heavy jobs should carry results between phases inside one workflow, unless a user decision requires a pause.

A `+Nk` budget sets a token ceiling, not a target to spend. Size each phase from its work list and the cookbook's sizing rules. Harness concurrency limits and the dynamic workflow size setting also affect execution. Large workflows can consume substantial tokens; start with a small smoke test when trying a new backend.

## Validate workflow scripts

From the repository directory, syntax-check the JavaScript examples embedded in `SKILL.md`:

```sh
python3 check-script.py
```

To check a workflow script before submitting it:

```sh
python3 check-script.py path/to/workflow.js
```

The checker wraps workflow code so Node.js can parse top-level `await` and `return`, then runs `node --check`. It checks JavaScript syntax only. It does not execute a workflow, validate the Workflow API, or verify backend compatibility.

## Backend compatibility

The harness provides orchestration, scheduling, and resume support. The backend must handle the model-side tool calls correctly.

- Verify every model alias used by a script. A proxy may route an alias to an unavailable model or to a different capability tier than expected.
- Treat Fable-tier routing as setup-dependent. The operator notes explicitly mark its environment-variable mapping as unverified.
- Check forced tool selection before relying on schema-based agent results. Unsupported selection can leave those results null.
- Check the harness's workflow size setting if runs stay smaller than requested. Installing the cookbook does not change that setting.

See [BACKEND-NOTES.md](BACKEND-NOTES.md) for the harness/backend boundary and a smoke test, and [OPERATOR-CHECKLIST.md](OPERATOR-CHECKLIST.md) for setup and troubleshooting. Dated observations in those documents are not a compatibility guarantee for other deployments.

## Repository contents

| File | Purpose |
| --- | --- |
| [SKILL.md](SKILL.md) | Model-facing cookbook with sizing guidance, workflow templates, and execution instructions. |
| [OPERATOR-CHECKLIST.md](OPERATOR-CHECKLIST.md) | Setup and troubleshooting checklist for the harness, backend routing, and workflow execution. |
| [BACKEND-NOTES.md](BACKEND-NOTES.md) | Backend compatibility notes, observed behavior, and a smoke test. |
| [check-script.py](check-script.py) | Utility for syntax-checking JavaScript workflow scripts and embedded examples with Node.js. |
