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

The optional stdio adapter runs locally and uses the same engine as the CLI.
Use **Fullbleed 2.5.1 or newer**: that release corrects the tool schemas rejected
by strict MCP clients in 2.5.0. Install in your
[virtual environment](../getting-started/installation.md#use-a-virtual-environment):

```bash
python -m pip install --upgrade "fullbleed>=2.5.1,<3" fullbleed-mcp
python -m fullbleed --version
python -c "import sys; print(sys.executable)"
```

In your client's **stdio server** settings, use the Python executable printed
above as the command. Set its argument list to:

```json
["-m", "fullbleed_mcp", "--root", "/absolute/path/to/documents"]
```

Replace the final argument with an existing document workspace. A Windows path
can use forward slashes, such as `C:/work/documents`. The client launches this
process; no server port, API key, or separate web service is required. Document
paths passed to tools are confined to this workspace.

If your client launches the core package directly, use arguments
`["-m", "fullbleed", "mcp", "--root", "/absolute/path/to/documents"]` instead.
Both entrypoints share the runtime implementation.

### Check the connection

After restarting the client, ask it to list the Fullbleed tools and call
`fullbleed_capabilities`. The installed engine reports its version and supported
capabilities. Use `fullbleed_agent_contract` for detailed tool schemas before
constructing requests.

| Task | Tool |
| --- | --- |
| Discover the installed engine | `fullbleed_capabilities` |
| Read argument and result schemas | `fullbleed_agent_contract` |
| Render a PDF and page images | `fullbleed_render_preview` |
| Inspect the generated PDF | `fullbleed_inspect` |
| Check a document against selected diagnostics | `fullbleed_verify` |

The [adapter README](https://github.com/fullbleed-engine/fullbleed-official/tree/master/packages/fullbleed-mcp)
also covers Docker and registry metadata. Its development checks use the official
MCP TypeScript client to exercise tool discovery, structured results, a rendered
PDF, and a tool error.

### Troubleshoot setup

| Symptom | Next step |
| --- | --- |
| Tool discovery rejects `outputSchema.type` | Upgrade the engine to 2.5.1 or newer in the same Python environment used by the client, then restart the client. |
| The client cannot find the command or module | Use the absolute Python executable from the installation environment; check that it can run `-m fullbleed_mcp --help`. |
| A tool rejects an input or output path | Keep the document and its assets inside the configured `--root` workspace. |
| A terminal appears to wait after starting the server | This is a stdio process waiting for protocol messages. Configure your MCP client to launch it. |

## Give the agent a concrete document task

> Use Fullbleed to create an invoice from my JSON. Discover the installed runtime first. Keep assets local, escape input text, render the PDF and PNG previews, inspect every page, and verify that the invoice number, line items, and total appear in the output. Return the PDF and any unresolved diagnostics.

Add the target page size, fonts, expected page count, and output profile when these matter.
For a stronger visual starting point, give the agent the
[Northstar invoice](../examples.md#styled-invoice) or
[Common Ground report](../examples.md#business-report) source bundle, including
its fonts. Ask it to preserve the design while replacing the fictional content
with your data.

## Evaluate the result

The [agent acceptance harness](https://github.com/fullbleed-engine/fullbleed-official/tree/master/agent_acceptance) and [AgentDocBench scaffold](https://github.com/fullbleed-engine/fullbleed-official/tree/master/agentdocbench) provide testable tasks and artifact checks. A generated PDF still needs output verification; successful tool calls alone do not establish document quality.
