import * as crypto from "node:crypto";
import * as net from "node:net";
import { BackendDescriptor, MAX_MESSAGE_BYTES, PROTOCOL_VERSION, RpcRequest, RpcResponse } from "../protocol";

const CHALLENGE = Buffer.from("#CHALLENGE#");
const WELCOME = Buffer.from("#WELCOME#");
const MAX_QUEUED_FRAMES = 8;

function responseForChallenge(challenge: Buffer, pairingToken: Buffer): Buffer {
  if (!challenge.subarray(0, CHALLENGE.length).equals(CHALLENGE)) throw new Error("Invalid IPC challenge");
  const message = challenge.subarray(CHALLENGE.length);
  const algorithmEnd = message.indexOf(125); // closing } in {sha256}
  const algorithm = algorithmEnd > 1 ? message.subarray(1, algorithmEnd).toString("ascii") : "";
  if (algorithm !== "sha256") throw new Error("Unsupported IPC authentication algorithm");
  return Buffer.concat([Buffer.from("{sha256}"), crypto.createHmac("sha256", pairingToken).update(message).digest()]);
}

class FramedSocket {
  private readonly frames: Buffer[] = [];
  private readonly waiters: Array<(frame: Buffer) => void> = [];

  constructor(private readonly socket: net.Socket) {
    socket.on("data", (chunk: Buffer) => {
      if (process.env.JARVIS_IPC_TRACE === "1") console.error(`JARVIS IPC received ${chunk.length} bytes: ${chunk.toString("hex")}`);
      this.consume(chunk);
    });
  }

  private consume(chunk: Buffer): void {
    // multiprocessing AF_PIPE uses Windows message-mode named pipes: each
    // send_bytes() payload arrives as one native message, without the POSIX
    // Connection 4-byte stream header. The backend independently enforces the
    // same bound before it accepts a message.
    if (chunk.length === 0 || chunk.length > MAX_MESSAGE_BYTES) {
      this.socket.destroy(new Error("IPC message exceeds the size limit"));
      return;
    }
    const waiter = this.waiters.shift();
    if (waiter) {
      waiter(chunk);
    } else if (this.frames.length < MAX_QUEUED_FRAMES) {
      this.frames.push(chunk);
    } else {
      this.socket.destroy(new Error("IPC receive queue is full"));
    }
  }

  read(timeoutMs: number): Promise<Buffer> {
    const available = this.frames.shift();
    if (available) return Promise.resolve(available);
    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => reject(new Error("IPC response timed out")), timeoutMs);
      this.waiters.push((frame) => { clearTimeout(timer); resolve(frame); });
    });
  }

  write(frame: Buffer): void {
    if (frame.length > MAX_MESSAGE_BYTES) throw new Error("IPC message exceeds the size limit");
    this.socket.write(frame);
  }
}

export class NamedPipeClient {
  private sequence = 0;
  private constructor(private readonly socket: net.Socket, private readonly framed: FramedSocket) {}

  static async connect(descriptor: BackendDescriptor, pairingToken: Buffer, timeoutMs = 3000): Promise<NamedPipeClient> {
    // Install the frame reader before connecting: AF_PIPE can send its
    // authentication challenge immediately after the connect completion.
    const socket = new net.Socket();
    const framed = new FramedSocket(socket);
    socket.connect(descriptor.pipe_name);
    await new Promise<void>((resolve, reject) => {
      const timer = setTimeout(() => reject(new Error("IPC connection timed out")), timeoutMs);
      socket.once("connect", () => { clearTimeout(timer); resolve(); });
      socket.once("error", (error) => { clearTimeout(timer); reject(error); });
    });
    const challenge = await framed.read(timeoutMs);
    framed.write(responseForChallenge(challenge, pairingToken));
    if (!(await framed.read(timeoutMs)).equals(WELCOME)) throw new Error("IPC pairing rejected");
    const reverseMessage = Buffer.concat([Buffer.from("{sha256}"), crypto.randomBytes(32)]);
    framed.write(Buffer.concat([CHALLENGE, reverseMessage]));
    const reverseResponse = await framed.read(timeoutMs);
    const expectedResponse = Buffer.concat([Buffer.from("{sha256}"), crypto.createHmac("sha256", pairingToken).update(reverseMessage).digest()]);
    if (!crypto.timingSafeEqual(reverseResponse, expectedResponse)) throw new Error("Invalid IPC authentication response");
    framed.write(WELCOME);
    const client = new NamedPipeClient(socket, framed);
    await client.call("initialize", { client_id: "VS_CODE_CLIENT", protocol_version: PROTOCOL_VERSION }, timeoutMs);
    return client;
  }

  async call(method: RpcRequest["method"], params: Record<string, unknown> = {}, timeoutMs = 3000): Promise<RpcResponse> {
    const id = `vscode-${++this.sequence}`;
    const request: RpcRequest = { jsonrpc: "2.0", id, method, params };
    this.framed.write(Buffer.from(JSON.stringify(request), "utf8"));
    const response = JSON.parse((await this.framed.read(timeoutMs)).toString("utf8")) as RpcResponse;
    if (response.jsonrpc !== "2.0" || response.id !== id) throw new Error("Invalid IPC response");
    return response;
  }

  close(): void { this.socket.destroy(); }
}
