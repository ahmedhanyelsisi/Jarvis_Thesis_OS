import * as childProcess from "node:child_process";
import * as crypto from "node:crypto";
import * as path from "node:path";
import * as vscode from "vscode";
import { BackendDescriptor } from "./protocol";
import { NamedPipeClient } from "./client/namedPipeClient";

export type BackendState = "CONNECTING" | "ONLINE" | "OFFLINE";

export class BackendController implements vscode.Disposable {
  state: BackendState = "OFFLINE";
  health = "Not connected";
  private client?: NamedPipeClient;
  private process?: childProcess.ChildProcessWithoutNullStreams;

  async start(context: vscode.ExtensionContext): Promise<void> {
    this.state = "CONNECTING";
    const python = vscode.workspace.getConfiguration("jarvisThesis").get<string>("pythonPath", "python");
    const launcher = path.resolve(context.extensionPath, "..", "backend", "ipc", "launcher.py");
    const pairingToken = crypto.randomBytes(32);
    const boundedEnv: NodeJS.ProcessEnv = {
      PATH: process.env.PATH,
      SystemRoot: process.env.SystemRoot,
      TEMP: process.env.TEMP,
      TMP: process.env.TMP,
      USERPROFILE: process.env.USERPROFILE,
      PYTHONUTF8: "1"
    };
    try {
      this.process = childProcess.spawn(python, ["-B", launcher], { cwd: path.dirname(launcher), env: boundedEnv, windowsHide: true, stdio: "pipe" });
      const descriptor = await this.readDescriptor(this.process, pairingToken);
      this.client = await NamedPipeClient.connect(descriptor, pairingToken);
      const response = await this.client.call("get_health");
      this.health = String(response.result?.backend ?? "ONLINE");
      this.state = "ONLINE";
    } catch (error) {
      this.health = error instanceof Error ? error.message : "Backend unavailable";
      this.state = "OFFLINE";
      this.dispose();
    }
  }

  async showHealth(): Promise<string> {
    if (!this.client) return `Backend: ${this.state}; Health: ${this.health}`;
    const response = await this.client.call("get_health");
    return JSON.stringify(response.result);
  }

  private readDescriptor(process: childProcess.ChildProcessWithoutNullStreams, pairingToken: Buffer): Promise<BackendDescriptor> {
    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => reject(new Error("Backend bootstrap timed out")), 3000);
      let output = "";
      process.stdout.on("data", (chunk: Buffer) => {
        output += chunk.toString("utf8");
        const line = output.indexOf("\n");
        if (line >= 0) {
          clearTimeout(timer);
          try { resolve(JSON.parse(output.slice(0, line)) as BackendDescriptor); } catch { reject(new Error("Invalid backend descriptor")); }
        }
      });
      process.once("error", (error) => { clearTimeout(timer); reject(error); });
      process.stdin.write(`${JSON.stringify({ pairing_token: pairingToken.toString("base64") })}\n`);
    });
  }

  dispose(): void {
    this.client?.close();
    this.client = undefined;
    this.process?.kill();
    this.process = undefined;
  }
}
