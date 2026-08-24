import { client } from "./client";

// `schema.d.ts` is not generated for the /api/v1/dev routes (see admin.ts for
// the same pattern), so these types are hand-kept in sync with
// backend/app/schemas/deployment.py.

export interface VersionCheck {
  github_repo: string;
  installed_version: string;
  latest_version: string | null;
  latest_notes: string | null;
  latest_url: string | null;
  latest_published_at: string | null;
  checked_at: string | null;
  is_stale: boolean;
  has_update: boolean;
}

export type DeploymentStage =
  | "idle"
  | "checking"
  | "downloading"
  | "verifying"
  | "migrating"
  | "deploying"
  | "health_checking"
  | "success"
  | "rolling_back"
  | "rollback_success"
  | "failed"
  | "unknown";

export type DeploymentErrorCode =
  | "download_failed"
  | "checksum_mismatch"
  | "load_failed"
  | "digest_mismatch"
  | "migration_failed"
  | "health_check_failed"
  | "rollback_failed"
  | "rollback_unavailable"
  | "interrupted"
  | "already_current"
  | "state_write_failed";

export interface DeploymentStatus extends VersionCheck {
  stage: DeploymentStage;
  action: string | null;
  requested_version: string | null;
  target_version: string | null;
  previous_version: string | null;
  started_at: string | null;
  updated_at: string | null;
  finished_at: string | null;
  error_code: string | null;
  error_message: string | null;
  is_busy: boolean;
  record_diverged: boolean;
  log_tail: string[];
}

export interface WriteRequestResponse {
  request_id: string;
}

// Same set as backend's DeploymentService.TERMINAL_STAGES / the updater's
// state.sh — lets the page tell a finished operation from a running one.
export const TERMINAL_STAGES: readonly DeploymentStage[] = [
  "idle",
  "success",
  "rollback_success",
  "failed",
];

/**
 * Thrown when the server answered with an HTTP error. Distinct from a transport
 * failure (backend down mid-deploy), because those two must render differently:
 * a 401/403 is a permission problem the user has to act on, not a restart to
 * wait out.
 */
export class DeploymentHttpError extends Error {
  constructor(
    readonly status: number,
    readonly body: unknown,
  ) {
    super(`Deployment API returned HTTP ${status}`);
    this.name = "DeploymentHttpError";
  }
}

export async function getDeploymentStatus(): Promise<DeploymentStatus> {
  const { data, error, response } = await (client.GET as any)("/api/v1/dev/deployment/status");

  if (error) {
    throw new DeploymentHttpError(response?.status ?? 0, error);
  }
  if (!data) {
    throw new Error("Deployment status response is empty.");
  }

  return data;
}

export async function checkDeploymentUpdate(): Promise<VersionCheck> {
  const { data, error } = await (client.POST as any)("/api/v1/dev/deployment/check");

  if (error) {
    throw error;
  }
  if (!data) {
    throw new Error("Deployment check response is empty.");
  }

  return data;
}

export async function requestDeploymentUpdate(version: string): Promise<WriteRequestResponse> {
  const { data, error } = await (client.POST as any)("/api/v1/dev/deployment/update", {
    body: { version },
  });

  if (error) {
    throw error;
  }
  if (!data) {
    throw new Error("Deployment update response is empty.");
  }

  return data;
}

export async function requestDeploymentRollback(): Promise<WriteRequestResponse> {
  const { data, error } = await (client.POST as any)("/api/v1/dev/deployment/rollback");

  if (error) {
    throw error;
  }
  if (!data) {
    throw new Error("Deployment rollback response is empty.");
  }

  return data;
}
