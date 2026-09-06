import * as assert from "node:assert";
import * as childProcess from "node:child_process";
import * as crypto from "node:crypto";
import * as fs from "node:fs";
import * as path from "node:path";
import test from "node:test";
import { NamedPipeClient } from "../src/client/namedPipeClient";
import { BackendDescriptor } from "../src/protocol";

function projectPython(): string {
  const executable = path.resolve(__dirname, "../../../../.venv/Scripts/python.exe");
  return fs.existsSync(executable) ? executable : "python";
}

function readDescriptor(process: childProcess.ChildProcessWithoutNullStreams, pairingToken: Buffer): Promise<BackendDescriptor> {
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => reject(new Error("launcher descriptor timed out")), 3000);
    let output = "";
    process.stdout.on("data", (chunk: Buffer) => {
      output += chunk.toString("utf8");
      const newline = output.indexOf("\n");
      if (newline < 0) return;
      clearTimeout(timer);
      try { resolve(JSON.parse(output.slice(0, newline)) as BackendDescriptor); }
      catch { reject(new Error("launcher emitted an invalid descriptor")); }
    });
    process.once("error", (error) => { clearTimeout(timer); reject(error); });
    process.stdin.write(`${JSON.stringify({ pairing_token: pairingToken.toString("base64") })}\n`);
  });
}

test("real Node client completes authenticated Python named-pipe health RPC", async () => {
  const launcher = path.resolve(__dirname, "../../../backend/ipc/launcher.py");
  const pairingToken = crypto.randomBytes(32);
  const process = childProcess.spawn(projectPython(), ["-B", launcher], {
    cwd: path.dirname(launcher), windowsHide: true, stdio: "pipe"
  });
  let client: NamedPipeClient | undefined;
  try {
    const descriptor = await readDescriptor(process, pairingToken);
    client = await NamedPipeClient.connect(descriptor, pairingToken);
    const health = await client.call("get_health");
    assert.deepStrictEqual(health.result, {
      backend: "ONLINE", jarvis_runtime: "NOT_ATTACHED", protocol_version: "28A.1"
    });
    const shutdown = await client.call("shutdown_if_owner", { owner_instance_id: descriptor.instance_id });
    assert.strictEqual(shutdown.result?.shutdown, true);
  } finally {
    client?.close();
    if (!process.killed) process.kill();
  }
});
