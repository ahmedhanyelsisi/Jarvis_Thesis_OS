import * as path from "node:path";
import { runTests } from "@vscode/test-electron";

async function main(): Promise<void> {
  await runTests({
    extensionDevelopmentPath: path.resolve(__dirname, "../.."),
    extensionTestsPath: path.resolve(__dirname, "./suite/index"),
    launchArgs: ["--disable-extensions"]
  });
}

void main();
