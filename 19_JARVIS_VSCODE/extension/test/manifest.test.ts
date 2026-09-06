import * as assert from "node:assert";
import * as fs from "node:fs";
import * as path from "node:path";
import test from "node:test";

test("manifest registers the minimal JARVIS view and health command", () => {
  const manifest = JSON.parse(fs.readFileSync(path.resolve(__dirname, "../../package.json"), "utf8"));
  assert.ok(manifest.contributes.viewsContainers.activitybar.some((view: { id: string }) => view.id === "jarvisThesis"));
  assert.ok(manifest.contributes.views.jarvisThesis.some((view: { id: string }) => view.id === "jarvisThesis.health"));
  assert.ok(manifest.contributes.commands.some((command: { command: string }) => command.command === "jarvisThesis.showHealth"));
});
