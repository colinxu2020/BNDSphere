import { type ReactNode, useEffect, useRef, useState } from "react";
import { motion } from "motion/react";
import {
  AlertTriangle,
  Clock,
  ExternalLink,
  GitBranch,
  Loader2,
  RefreshCw,
  Rocket,
  Server,
  Tag,
} from "@/src/components/ui/Icons";
import {
  DeploymentHttpError,
  checkDeploymentUpdate,
  getDeploymentStatus,
  type DeploymentErrorCode,
  type DeploymentStage,
  type DeploymentStatus,
} from "../api/deployment";
import { formatDate } from "../lib/format";
import {
  Badge,
  PageHeader,
  SecondaryButton,
  StatusMessage,
  Surface,
} from "../components/ui/AppPrimitives";
import { cn } from "../lib/utils";

const POLL_IDLE_MS = 60_000;
const POLL_BUSY_MS = 3_000;

const STAGE_LABELS: Record<DeploymentStage, string> = {
  idle: "空闲",
  checking: "检查更新中",
  downloading: "下载中",
  verifying: "校验中",
  migrating: "数据库迁移中",
  deploying: "部署中",
  health_checking: "健康检查中",
  success: "更新成功",
  rolling_back: "回滚中",
  rollback_success: "回滚成功",
  failed: "失败",
  unknown: "状态未知",
};

const ERROR_CODE_LABELS: Record<DeploymentErrorCode, string> = {
  download_failed: "下载失败",
  checksum_mismatch: "校验和不匹配",
  load_failed: "镜像加载失败",
  digest_mismatch: "镜像摘要不匹配",
  migration_failed: "数据库迁移失败",
  health_check_failed: "健康检查未通过",
  rollback_failed: "回滚失败",
  rollback_unavailable: "没有可回滚的版本",
  interrupted: "操作被中断",
  already_current: "已经是当前版本",
  state_write_failed: "状态写入失败",
  deploy_failed: "容器重建失败",
  record_diverged: "部署记录与运行中的容器不一致",
  orphan_reap_failed: "残留的一次性容器无法清除",
};

const ACTION_LABELS: Record<string, string> = {
  update: "更新",
  rollback: "回滚",
};

function stageTone(stage: DeploymentStage): "slate" | "yellow" | "green" | "red" | "blue" {
  if (stage === "success" || stage === "rollback_success") return "green";
  if (stage === "failed") return "red";
  if (stage === "idle") return "slate";
  if (stage === "unknown") return "yellow";
  return "blue";
}

function deliveryPathText(status: DeploymentStatus): string | null {
  if (!status.action) return null;
  const label = ACTION_LABELS[status.action] || status.action;
  const from = status.previous_version;
  const to = status.target_version || status.requested_version;
  if (from && to) return `${label}：${from} → ${to}`;
  if (to) return `${label}：${to}`;
  return label;
}

function errorText(status: DeploymentStatus): string | null {
  if (!status.error_code && !status.error_message) return null;
  const codeLabel = status.error_code
    ? ERROR_CODE_LABELS[status.error_code as DeploymentErrorCode] || status.error_code
    : null;
  if (codeLabel && status.error_message) return `${codeLabel}：${status.error_message}`;
  return codeLabel || status.error_message;
}

// GitHub release URLs look like https://github.com/{owner}/{repo}/releases/tag/{tag}.
// The API never exposes the repo directly, so it's derived from the release
// link when one is known; otherwise there is nothing to show yet.
function repoInfoFromUrl(url: string | null): { label: string; href: string } | null {
  if (!url) return null;
  try {
    const parsed = new URL(url);
    if (parsed.hostname !== "github.com") return null;
    const [owner, repo] = parsed.pathname.split("/").filter(Boolean);
    if (!owner || !repo) return null;
    return { label: `${owner}/${repo}`, href: `https://github.com/${owner}/${repo}` };
  } catch {
    return null;
  }
}

export function DevPanel() {
  const [status, setStatus] = useState<DeploymentStatus | null>(null);
  const [unreachable, setUnreachable] = useState(false);
  const [httpError, setHttpError] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [checking, setChecking] = useState(false);
  const [actionMessage, setActionMessage] = useState<unknown>(null);
  const [actionTone, setActionTone] = useState<"error" | "success" | "info">("info");

  const statusRef = useRef<DeploymentStatus | null>(null);
  const unreachableRef = useRef(false);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const mountedRef = useRef(true);
  const pollNowRef = useRef<() => void>(() => {});

  useEffect(() => {
    mountedRef.current = true;

    const poll = async () => {
      if (timerRef.current) clearTimeout(timerRef.current);
      try {
        const next = await getDeploymentStatus();
        if (!mountedRef.current) return;
        statusRef.current = next;
        unreachableRef.current = false;
        setStatus(next);
        setUnreachable(false);
        setHttpError(null);
      } catch (err) {
        if (!mountedRef.current) return;
        // Only a TRANSPORT failure means "the backend is being replaced".
        // An HTTP status means the server answered and is emphatically up —
        // reporting a 401 as "restarting, please wait" leaves the user
        // watching a spinner forever for something a login would fix.
        if (err instanceof DeploymentHttpError) {
          unreachableRef.current = false;
          setUnreachable(false);
          setHttpError(err.status);
        } else {
          // The backend is one of the containers replaced during an update —
          // it will stop answering mid-deploy. That is expected, not an
          // error: keep the last known status on screen, flag it quietly,
          // and poll fast until it answers again.
          unreachableRef.current = true;
          setUnreachable(true);
        }
      } finally {
        if (mountedRef.current) {
          setLoading(false);
          const busy = unreachableRef.current || statusRef.current?.is_busy;
          timerRef.current = setTimeout(poll, busy ? POLL_BUSY_MS : POLL_IDLE_MS);
        }
      }
    };

    pollNowRef.current = poll;
    poll();

    return () => {
      mountedRef.current = false;
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, []);

  const runCheck = async () => {
    setChecking(true);
    setActionTone("info");
    setActionMessage(null);
    try {
      const check = await checkDeploymentUpdate();
      setStatus((prev) => (prev ? { ...prev, ...check } : prev));
    } catch (error) {
      setActionTone("error");
      setActionMessage(error);
    } finally {
      setChecking(false);
    }
  };

  if (loading && !status) {
    return (
      <div className="flex flex-col items-center justify-center gap-3 py-24 text-slate-500">
        <Loader2 size={28} className="animate-spin" />
        <p className="text-sm font-medium">正在加载部署状态…</p>
      </div>
    );
  }

  // github_repo comes straight from the API so the card is never blank on an
  // install that has no releases yet; the URL derivation is only a fallback.
  const repoInfo = status?.github_repo
    ? { label: status.github_repo, href: `https://github.com/${status.github_repo}` }
    : repoInfoFromUrl(status?.latest_url ?? null);
  const path = status ? deliveryPathText(status) : null;
  const error = status ? errorText(status) : null;

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className="grid min-w-0 gap-6 pb-20"
    >
      <PageHeader
        eyebrow="Dev"
        title="部署面板"
        description="查看当前环境的版本与最近一次部署状态；部署在 GitHub 上执行"
      />

      {httpError !== null && (
        <StatusMessage
          tone="error"
          value={
            httpError === 401
              ? "登录状态已失效，请重新登录后再查看部署面板。"
              : httpError === 403
                ? "当前账号没有开发者权限，无法查看或操作部署面板。"
                : `部署接口返回错误（HTTP ${httpError}），请稍后重试。`
          }
        />
      )}

      {unreachable && (
        <StatusMessage tone="info" value="后端服务正在重启，等待其恢复中，页面会持续自动刷新…" />
      )}

      {status?.record_diverged && (
        <div className="flex items-start gap-2 rounded-md border border-yellow-100 bg-yellow-50 p-4 text-sm font-medium text-yellow-800">
          <AlertTriangle size={18} className="mt-0.5 shrink-0" />
          <span>记录的部署版本与实际运行版本不一致，请检查日志确认真实状态。回滚已被禁用。</span>
        </div>
      )}

      {actionMessage != null && <StatusMessage value={actionMessage} tone={actionTone} />}

      {status && (
        <>
          <div className="grid min-w-0 gap-4 md:grid-cols-3">
            <Surface className="p-5">
              <div className="flex items-center gap-2 text-slate-500">
                <GitBranch size={16} />
                <span className="text-xs font-bold uppercase tracking-wider">代码仓库</span>
              </div>
              {repoInfo ? (
                <a
                  href={repoInfo.href}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="mt-2 inline-flex items-center gap-1 text-lg font-display font-bold text-slate-900 hover:text-primary-600"
                >
                  {repoInfo.label}
                  <ExternalLink size={14} />
                </a>
              ) : (
                <p className="mt-2 text-lg font-display font-bold text-slate-400">未知</p>
              )}
            </Surface>

            <Surface className="p-5">
              <div className="flex items-center gap-2 text-slate-500">
                <Server size={16} />
                <span className="text-xs font-bold uppercase tracking-wider">当前版本</span>
              </div>
              <p className="mt-2 text-lg font-display font-bold text-slate-900">
                {status.installed_version}
              </p>
              {status.record_diverged && <Badge tone="red">状态不一致</Badge>}
            </Surface>

            <Surface className="p-5">
              <div className="flex items-center gap-2 text-slate-500">
                <Tag size={16} />
                <span className="text-xs font-bold uppercase tracking-wider">最新发布</span>
              </div>
              <p className="mt-2 text-lg font-display font-bold text-slate-900">
                {status.latest_version || "暂无发布"}
              </p>
              <div className="mt-1 flex flex-wrap items-center gap-2">
                {status.has_update && <Badge tone="green">有更新可用</Badge>}
                {status.is_stale && (
                  <span className="text-xs text-slate-400">数据可能不是最新</span>
                )}
              </div>
            </Surface>
          </div>

          <Surface className="grid gap-3">
            <h2 className="font-display text-lg font-bold text-slate-900">运行详情</h2>
            <DetailRow label="状态">
              <Badge tone={stageTone(status.stage)}>
                {STAGE_LABELS[status.stage] || status.stage}
              </Badge>
            </DetailRow>
            {path && <DetailRow label="更新路径">{path}</DetailRow>}
            {error && (
              <DetailRow label="错误">
                <span className="text-red-700">{error}</span>
              </DetailRow>
            )}
            <DetailRow label="上次完成时间">
              <span className="inline-flex items-center gap-1.5">
                <Clock size={14} className="text-slate-400" />
                {formatDate(status.finished_at)}
              </span>
            </DetailRow>
          </Surface>

          {status.latest_version && (
            <Surface className="grid gap-3">
              <div className="flex items-center justify-between gap-3">
                <h2 className="font-display text-lg font-bold text-slate-900">
                  发行说明 · {status.latest_version}
                </h2>
                {status.latest_url && (
                  <a
                    href={status.latest_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1 text-sm font-semibold text-primary-600 hover:text-primary-700"
                  >
                    查看发布页面 <ExternalLink size={14} />
                  </a>
                )}
              </div>
              <p className="whitespace-pre-wrap text-sm text-slate-600">
                {status.latest_notes || "本次发布没有提供说明"}
              </p>
              {status.latest_published_at && (
                <p className="text-xs text-slate-400">
                  发布时间：{formatDate(status.latest_published_at)}
                </p>
              )}
            </Surface>
          )}

          {/* This panel reports; it does not deploy. Updates and rollbacks are
              run from the Deploy workflow on GitHub, so the only action here is
              a link to it — there is no request this page can send that would
              start one. */}
          <div className="flex flex-wrap items-center gap-3">
            <a
              href={status.workflow_runs_url}
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center justify-center gap-2 rounded-md bg-primary-500 px-5 py-3 font-semibold text-white shadow-md shadow-primary-500/20 transition-all hover:bg-primary-600 active:scale-[0.98]"
            >
              <Rocket size={16} />
              在 GitHub 上运行部署
              <ExternalLink size={14} />
            </a>
            <SecondaryButton onClick={runCheck} disabled={checking}>
              <RefreshCw size={16} className={cn(checking && "animate-spin")} />
              检查更新
            </SecondaryButton>
          </div>
          <p className="text-xs text-slate-500">
            部署与回滚均在 GitHub Actions 的 Deploy 工作流中手动触发：
            {status.has_update && status.latest_version
              ? ` action=update，version=${status.latest_version}`
              : status.latest_version
                ? " 当前已是最新版本"
                : " 暂无可用发布"}
            {status.previous_version && !status.record_diverged
              ? `；如需回滚，使用 action=rollback，version=${status.previous_version}`
              : ""}
          </p>

          <Surface className="p-5">
            <h2 className="mb-2 text-xs font-bold uppercase tracking-wider text-slate-500">
              运行日志
            </h2>
            <div className="max-h-80 overflow-y-auto font-mono text-xs leading-relaxed text-slate-700">
              {status.log_tail.length ? (
                status.log_tail.map((line, index) => (
                  <div key={index} className="whitespace-pre-wrap break-all">
                    {line}
                  </div>
                ))
              ) : (
                <p className="text-slate-400">暂无日志</p>
              )}
            </div>
          </Surface>
        </>
      )}
    </motion.div>
  );
}

function DetailRow({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="flex flex-col gap-1 border-b border-slate-100 pb-3 last:border-0 last:pb-0 sm:flex-row sm:items-center sm:justify-between">
      <span className="text-sm font-semibold text-slate-500">{label}</span>
      <span className="text-sm font-medium text-slate-900">{children}</span>
    </div>
  );
}
