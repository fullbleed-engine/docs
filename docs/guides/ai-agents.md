---
description: Set up Fullbleed for coding agents using installed-runtime discovery, the bundled Agent Skill, or the optional MCP adapter.
---
# Use Fullbleed with a coding agent

An agent can discover the actual installed version, commands, schemas, profiles, examples, and limitations before writing document code.

```bash
python -m pip install fullbleed
python -m fullbleed agent-contract --format json
python -m fullbleed capabilities --json
```

## Install the bundled Agent Skill

Export it to an absent or empty directory used by your agent:

```bash
python -m fullbleed agent export-skill .agents/skills/fullbleed --json
```

The [versionless Skill](https://github.com/fullbleed-engine/fullbleed-official/blob/master/skills/fullbleed/SKILL.md) teaches selection, authoring, rendering, previewing, diagnostics, and verification. It points back to installed-runtime discovery for capability facts.

## Connect through MCP

The optional stdio adapter is separately distributed:

```bash
python -m pip install fullbleed-mcp
fullbleed-mcp --root .
```

Use the absolute workspace path when configuring your MCP client. See the [adapter README](https://github.com/fullbleed-engine/fullbleed-official/tree/master/packages/fullbleed-mcp) for client setup and tool definitions. The core also includes `python -m fullbleed mcp --root .`.

## Give the agent a concrete document task

> Use Fullbleed to create an invoice from my JSON. Discover the installed runtime first. Keep assets local, escape input text, render the PDF and PNG previews, inspect every page, and verify that the invoice number, line items, and total appear in the output. Return the PDF and any unresolved diagnostics.

Add the target page size, fonts, expected page count, and output profile when these matter. Use the [complete workflow examples](../examples.md) as runnable starting points.

## Evaluate the result

The [agent acceptance harness](https://github.com/fullbleed-engine/fullbleed-official/tree/master/agent_acceptance) and [AgentDocBench scaffold](https://github.com/fullbleed-engine/fullbleed-official/tree/master/agentdocbench) provide testable tasks and artifact checks. A generated PDF still needs output verification; successful tool calls alone do not establish document quality.
