import * as assert from "node:assert";
import * as vscode from "vscode";

suite("JARVIS extension activation", () => {
  test("activates and registers Show Health", async () => {
    const extension = vscode.extensions.getExtension("jarvis-thesis-os.jarvis-thesis-vscode");
    assert.ok(extension);
    await extension.activate();
    assert.ok((await vscode.commands.getCommands(true)).includes("jarvisThesis.showHealth"));
  });
});
