import * as vscode from "vscode";
import { BackendController } from "./backendController";
import { PROTOCOL_VERSION } from "./protocol";

class HealthView implements vscode.TreeDataProvider<vscode.TreeItem> {
  private readonly changed = new vscode.EventEmitter<void>();
  readonly onDidChangeTreeData = this.changed.event;
  constructor(private readonly backend: BackendController) {}
  refresh(): void { this.changed.fire(); }
  getTreeItem(item: vscode.TreeItem): vscode.TreeItem { return item; }
  getChildren(): vscode.TreeItem[] {
    return [
      new vscode.TreeItem("JARVIS"),
      new vscode.TreeItem(`Backend: ${this.backend.state}`),
      new vscode.TreeItem(`Protocol: ${PROTOCOL_VERSION}`),
      new vscode.TreeItem(`Health: ${this.backend.health}`)
    ];
  }
}

export async function activate(context: vscode.ExtensionContext): Promise<void> {
  const backend = new BackendController();
  const view = new HealthView(backend);
  context.subscriptions.push(backend, vscode.window.registerTreeDataProvider("jarvisThesis.health", view));
  context.subscriptions.push(vscode.commands.registerCommand("jarvisThesis.showHealth", async () => {
    vscode.window.showInformationMessage(await backend.showHealth());
  }));
  void backend.start(context).finally(() => view.refresh());
}

export function deactivate(): void {}
