export const PROTOCOL_VERSION = "28A.1";
export const MAX_MESSAGE_BYTES = 64 * 1024;

export type RpcId = string | number;

export interface RpcRequest {
  jsonrpc: "2.0";
  id: RpcId;
  method: "initialize" | "ping" | "get_version" | "get_health" | "detach" | "shutdown_if_owner";
  params?: Record<string, unknown>;
}

export interface RpcResponse {
  jsonrpc: "2.0";
  id: RpcId;
  result?: Record<string, unknown>;
  error?: { code: number; message: string };
}

export interface BackendDescriptor {
  protocol_version: string;
  backend_version: string;
  instance_id: string;
  pipe_name: string;
  owner_pid: number;
  started_at: string;
}
