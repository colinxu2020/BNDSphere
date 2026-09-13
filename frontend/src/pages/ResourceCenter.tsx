import { useEffect, useRef, useState, type FormEvent } from "react";
import { motion } from "motion/react";
import {
  Download,
  FileText,
  FileUp,
  Folder,
  Loader2,
  Search,
  Trash2,
} from "@/src/components/ui/Icons";
import { client } from "../api/client";
import { uploadFileWithDetails } from "../api/uploads";
import type { components } from "../api/schema";
import {
  DangerButton,
  EmptyState,
  PageHeader,
  PrimaryButton,
  StatusMessage,
  Surface,
  inputClassName,
} from "../components/ui/AppPrimitives";
import { formatDateTime } from "../lib/format";

type ResourceFile = components["schemas"]["ResourceFileInfo"];
type UserInfo = components["schemas"]["UserInfo"];

const MAX_FILE_SIZE = 50 * 1024 * 1024;

export function ResourceCenter() {
  const inputRef = useRef<HTMLInputElement>(null);
  const [resources, setResources] = useState<ResourceFile[]>([]);
  const [user, setUser] = useState<UserInfo | null>(null);
  const [search, setSearch] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [isUploading, setIsUploading] = useState(false);
  const [deletingId, setDeletingId] = useState<number | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const canManage =
    user?.role === "federation_staff" || user?.role === "admin" || user?.role === "dev";

  const loadResources = async (query?: string) => {
    setIsLoading(true);
    setError(null);
    try {
      const { data, error: requestError } = await client.GET("/api/v1/resources/", {
        params: { query: { search: query || undefined, size: 100 } },
      });
      if (requestError) {
        setError(requestError);
        return;
      }
      setResources(data?.items || []);
    } catch (requestError) {
      setError(requestError);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    void loadResources();

    if (!localStorage.getItem("bnd_token")) return;
    let cancelled = false;
    void client.GET("/api/v1/users/me").then(({ data }) => {
      if (!cancelled) setUser(data || null);
    });
    return () => {
      cancelled = true;
    };
  }, []);

  const submitSearch = (event: FormEvent) => {
    event.preventDefault();
    void loadResources(search.trim());
  };

  const uploadSelectedFile = async (files: FileList | null) => {
    const file = files?.[0];
    if (!file) return;

    setError(null);
    setSuccess(null);
    if (file.size > MAX_FILE_SIZE) {
      setError("单个文件不能超过 50MB");
      if (inputRef.current) inputRef.current.value = "";
      return;
    }

    setIsUploading(true);
    try {
      const uploaded = await uploadFileWithDetails(file, "resource_file");
      const { data, error: createError } = await client.POST("/api/v1/resources/", {
        body: {
          filename: file.name,
          object_key: uploaded.objectKey,
          content_type: file.type || "application/octet-stream",
        },
      });
      if (createError) {
        setError(createError);
        return;
      }
      if (data) setResources((current) => [data, ...current]);
      setSuccess(`“${file.name}”已上传`);
    } catch (uploadError) {
      setError(uploadError);
    } finally {
      setIsUploading(false);
      if (inputRef.current) inputRef.current.value = "";
    }
  };

  const deleteResource = async (resource: ResourceFile) => {
    if (!window.confirm(`确认删除“${resource.filename}”？删除后将无法下载。`)) return;

    setDeletingId(resource.id);
    setError(null);
    setSuccess(null);
    try {
      const { error: deleteError } = await client.DELETE("/api/v1/resources/{resource_id}", {
        params: { path: { resource_id: resource.id } },
      });
      if (deleteError) {
        setError(deleteError);
        return;
      }
      setResources((current) => current.filter((item) => item.id !== resource.id));
      setSuccess(`“${resource.filename}”已删除`);
    } catch (deleteError) {
      setError(deleteError);
    } finally {
      setDeletingId(null);
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className="grid gap-6 pb-20 md:pb-0"
    >
      <PageHeader
        eyebrow="RESOURCE CENTER"
        title="资料中心"
        description="查找并下载社团联合会发布的文件资料。"
        action={
          canManage ? (
            <>
              <input
                ref={inputRef}
                type="file"
                className="hidden"
                onChange={(event) => void uploadSelectedFile(event.target.files)}
              />
              <PrimaryButton
                type="button"
                loading={isUploading}
                onClick={() => inputRef.current?.click()}
              >
                <FileUp size={18} /> 上传资料
              </PrimaryButton>
            </>
          ) : undefined
        }
      />

      {canManage && <p className="text-sm text-slate-500">支持任意文件格式，单个文件最大 50MB。</p>}
      <StatusMessage value={error} />
      <StatusMessage value={success} tone="success" />

      <Surface>
        <form onSubmit={submitSearch} className="mb-6 flex flex-col gap-3 sm:flex-row">
          <label className="relative min-w-0 flex-1">
            <span className="sr-only">搜索资料</span>
            <Search
              size={18}
              className="pointer-events-none absolute left-4 top-1/2 -translate-y-1/2 text-slate-400"
            />
            <input
              className={`${inputClassName} pl-11`}
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="按文件名搜索"
            />
          </label>
          <PrimaryButton type="submit" className="shadow-none">
            搜索
          </PrimaryButton>
        </form>

        {isLoading ? (
          <div className="flex items-center justify-center py-20 text-slate-400">
            <Loader2 size={24} className="animate-spin" />
          </div>
        ) : resources.length ? (
          <div className="divide-y divide-slate-100 rounded-md border border-slate-100">
            {resources.map((resource) => (
              <article
                key={resource.id}
                className="flex flex-col gap-4 p-4 sm:flex-row sm:items-center sm:justify-between"
              >
                <div className="flex min-w-0 items-start gap-3">
                  <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-md bg-primary-50 text-primary-600">
                    <FileText size={22} />
                  </div>
                  <div className="min-w-0">
                    <h2 className="break-words font-semibold text-slate-900">
                      {resource.filename}
                    </h2>
                    <p className="mt-1 text-xs text-slate-500">
                      {formatFileSize(resource.file_size)} · {formatDateTime(resource.created_at)}
                    </p>
                  </div>
                </div>
                <div className="flex shrink-0 gap-2">
                  <a
                    href={`/api/v1/resources/${resource.id}/download`}
                    className="inline-flex items-center justify-center gap-2 rounded-md bg-primary-500 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-primary-600"
                  >
                    <Download size={17} /> 下载
                  </a>
                  {canManage && (
                    <DangerButton
                      type="button"
                      disabled={deletingId === resource.id}
                      onClick={() => void deleteResource(resource)}
                      aria-label={`删除 ${resource.filename}`}
                    >
                      <Trash2 size={17} /> 删除
                    </DangerButton>
                  )}
                </div>
              </article>
            ))}
          </div>
        ) : (
          <EmptyState
            title={search ? "没有找到匹配的资料" : "暂无资料"}
            description={search ? "请尝试其他关键词。" : "社团联合会发布资料后会显示在这里。"}
            icon={<Folder size={24} />}
          />
        )}
      </Surface>
    </motion.div>
  );
}

function formatFileSize(bytes: number) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}
