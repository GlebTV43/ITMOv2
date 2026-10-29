// Practice 04 — check-after-edit hook
// Runs scripts/check.py after any write/edit/apply_patch tool invocation.
// Appends audit JSONL to results/hook.jsonl.
// Compatible with OpenCode 2.0.18 V2 plugin API.

import { spawnSync } from "node:child_process";
import { appendFileSync, mkdirSync } from "node:fs";
import { join } from "node:path";

const WRITE_TOOLS = new Set(["write", "edit", "apply_patch"]);
const RUNNER_TIMEOUT = 30_000;

export default {
  id: "practice04.check-after-edit",

  async setup(ctx) {
    await ctx.tool.hook("execute.after", async (event) => {
      // Only trigger on write/edit/apply_patch
      const toolName = typeof event.tool === "string" ? event.tool : event.tool?.name ?? "";
      if (!WRITE_TOOLS.has(toolName)) return;
      if (event.status !== "completed" || event.result == null) return;

      const labDir = ctx.location?.directory ?? process.cwd();
      const python = process.env.P04_PYTHON ?? "python";
      const runnerPath = join(labDir, "scripts", "check.py");

      // Ensure results dir exists
      const resultsDir = join(labDir, "results");
      try { mkdirSync(resultsDir, { recursive: true }); } catch (_) {}

      const auditPath = join(resultsDir, "hook.jsonl");

      let status = "PASS";
      let exitCode = 0;
      let output = "";

      try {
        const result = spawnSync(python, [runnerPath], {
          cwd: labDir,
          encoding: "utf8",
          timeout: RUNNER_TIMEOUT,
        });

        exitCode = result.status ?? -1;
        output = (result.stdout ?? "") + (result.stderr ?? "");

        if (result.error) {
          status = "FAIL";
          output = `Runner could not start: ${result.error.message}\n${output}`;
          exitCode = -1;
        } else if (exitCode !== 0) {
          status = "FAIL";
        }
      } catch (err) {
        status = "FAIL";
        output = `Hook internal error: ${err?.message ?? err}`;
        exitCode = -1;
      }

      // Append audit JSONL
      const auditEntry = JSON.stringify({
        timestamp: new Date().toISOString(),
        tool: toolName,
        sessionID: event.sessionID ?? null,
        callID: event.callID ?? event.id ?? null,
        status,
        exitCode,
        output,  // full output, no truncation
      });
      try { appendFileSync(auditPath, auditEntry + "\n", "utf8"); } catch (_) {}

      // Append result to event so agent sees it
      const tag = `\n[AUTOCHECK ${status}]\n${output}`;
      if (event.result != null) {
        if (typeof event.result.content === "string") {
          event.result.content += tag;
        } else if (Array.isArray(event.result.content)) {
          const last = event.result.content[event.result.content.length - 1];
          if (last && typeof last.text === "string") {
            last.text += tag;
          } else {
            event.result.content.push({ type: "text", text: tag });
          }
        } else {
          // Fallback: attach as extra field for visibility
          event.result._autocheck = { status, exitCode, output };
        }
      }
    });
  },
};
