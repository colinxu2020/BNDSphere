import React, { useEffect, useMemo, useState } from "react";
import { motion } from "motion/react";
import {
  Bell,
  CalendarDays,
  RefreshCw,
  Save,
  Shield,
  Trash2,
  Users,
} from "@/src/components/ui/Icons";
import { client } from "../api/client";
import type { components } from "../api/schema";
import {
  ACTIVITY_LEVEL_MAP,
  ACTIVITY_LEVEL_OPTIONS,
  CLUB_STATUS_MAP,
  CLUB_STATUS_OPTIONS,
  ROLE_MAP,
  ROLE_OPTIONS,
  STAR_LEVEL_OPTIONS,
} from "../lib/labels";
import {
  formatDate,
  fromDateTimeLocalValue,
  nullableText,
  toDateTimeLocalValue,
} from "../lib/format";
import {
  Badge,
  Field,
  PageHeader,
  PrimaryButton,
  SecondaryButton,
  StatusMessage,
  inputClassName,
  selectClassName,
  textareaClassName,
} from "../components/ui/AppPrimitives";
import { FileUploadField } from "../components/ui/FileUploadField";
import { cn } from "../lib/utils";

type UserInfo = components["schemas"]["UserInfo"];
type Role = components["schemas"]["RoleEnum"];
type ClubInfo = components["schemas"]["ClubInfo"];
type ClubStarLevel = components["schemas"]["ClubStarLevelEnum"];
type ClubStatus = components["schemas"]["ClubStatusEnum"];
type AdminUserUpdate = components["schemas"]["AdminUserUpdate"];
type AdminClubUpdate = components["schemas"]["AdminClubUpdate"];
type AcademicTerm = components["schemas"]["AcademicTermInfo"];
type AcademicTermUpdate = components["schemas"]["AcademicTermUpdate"];
type GeneralActivity = components["schemas"]["GeneralActivityInfo"];
type GeneralActivityLevel = components["schemas"]["GeneralActivityLevelEnum"];
type Announcement = components["schemas"]["AnnouncementInfo"];

type SectionId = "users" | "clubs" | "terms" | "activities" | "announcements";

const sections: { id: SectionId; label: string; icon: React.ReactNode }[] = [
  { id: "users", label: "用户", icon: <Users size={16} /> },
  { id: "clubs", label: "社团", icon: <Shield size={16} /> },
  { id: "terms", label: "学期", icon: <CalendarDays size={16} /> },
  { id: "activities", label: "大型活动", icon: <CalendarDays size={16} /> },
  { id: "announcements", label: "公告", icon: <Bell size={16} /> },
];

export function Admin() {
  const [activeSection, setActiveSection] = useState<SectionId>("users");
  const [message, setMessage] = useState<unknown>(null);
  const [messageTone, setMessageTone] = useState<"error" | "success" | "info">(
    "info",
  );
  const [isRefreshing, setIsRefreshing] = useState(false);

  const setResult = (error: unknown, data: unknown) => {
    setMessageTone(error ? "error" : "success");
    setMessage(error || data || "操作已完成");
  };

  const checkHealth = async () => {
    setMessage(null);
    setMessageTone("info");
    setMessage("正在检查服务状态...");
    try {
      const { error, response } = await client.GET("/health", {
        parseAs: "text",
      });
      if (response.ok) {
        setMessageTone("success");
        setMessage(`服务正常（HTTP ${response.status}）`);
      } else {
        setMessageTone("error");
        setMessage(error || `健康检查失败（HTTP ${response.status}）`);
      }
    } catch (error) {
      setMessageTone("error");
      setMessage(error || "无法连接后端健康检查接口，请确认后端服务正在运行");
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className="grid min-w-0 gap-6"
    >
      <PageHeader
        eyebrow="Admin"
        title="管理员控制台"
        action={
          <SecondaryButton type="button" onClick={checkHealth}>
            <RefreshCw size={16} /> 健康检查
          </SecondaryButton>
        }
      />

      {message && <StatusMessage value={message} tone={messageTone} />}

      <div className="grid min-w-0 gap-5 lg:grid-cols-[220px_minmax(0,1fr)]">
        <aside className="h-fit rounded-md border border-edge bg-surface p-2">
          {sections.map((section) => (
            <button
              key={section.id}
              type="button"
              onClick={() => setActiveSection(section.id)}
              className={cn(
                "flex w-full items-center gap-2 rounded-md px-3 py-2 text-left text-sm font-semibold transition",
                activeSection === section.id
                  ? "bg-surface-inverted text-content-on-inverted"
                  : "text-content-muted hover:bg-surface-sunken",
              )}
            >
              {section.icon}
              {section.label}
            </button>
          ))}
        </aside>

        <section className="min-w-0 overflow-hidden rounded-md border border-edge bg-surface p-5">
          <RefreshContext.Provider
            value={{
              isRefreshing,
              refreshStart: () => setIsRefreshing(true),
              refreshEnd: () => setIsRefreshing(false),
              setResult,
            }}
          >
            {activeSection === "users" && <UsersAdmin />}
            {activeSection === "clubs" && <ClubsAdmin />}
            {activeSection === "terms" && <TermsAdmin />}
            {activeSection === "activities" && <ActivitiesAdmin />}
            {activeSection === "announcements" && <AnnouncementsAdmin />}
          </RefreshContext.Provider>
        </section>
      </div>
    </motion.div>
  );
}

const RefreshContext = React.createContext<{
  isRefreshing: boolean;
  refreshStart: () => void;
  refreshEnd: () => void;
  setResult: (error: unknown, data: unknown) => void;
}>({
  isRefreshing: false,
  refreshStart: () => {},
  refreshEnd: () => {},
  setResult: () => {},
});

function UsersAdmin() {
  const { isRefreshing, refreshStart, refreshEnd, setResult } =
    React.useContext(RefreshContext);
  const [users, setUsers] = useState<UserInfo[]>([]);
  const [search, setSearch] = useState("");
  const [selected, setSelected] = useState<UserInfo | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [form, setForm] = useState({
    username: "",
    email: "",
    avatar_uri: "",
    description: "",
    role: "" as Role | "",
  });

  const loadUsers = async () => {
    refreshStart();
    try {
      const { data, error } = await client.GET("/api/v1/admin/users/", {
        params: { query: { size: 50, search: search || undefined } },
      });
      if (error) setResult(error, null);
      setUsers(data?.items || []);
      if (selected) {
        const nextSelected =
          data?.items.find((item) => item.id === selected.id) || null;
        if (nextSelected) selectUser(nextSelected);
      }
    } catch (error) {
      setResult(error, null);
    } finally {
      refreshEnd();
    }
  };

  useEffect(() => {
    loadUsers();
  }, []);

  const selectUser = (user: UserInfo) => {
    setSelected(user);
    setForm({
      username: user.username || "",
      email: user.email || "",
      avatar_uri: user.avatar_uri || "",
      description: user.description || "",
      role: user.role,
    });
  };

  const saveUser = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!selected) return;
    setIsSaving(true);
    const body: AdminUserUpdate = {
      username: nullableText(form.username),
      email: nullableText(form.email),
      avatar_uri: nullableText(form.avatar_uri),
      description: nullableText(form.description),
      role: form.role || null,
    };
    try {
      const { data, error } = await client.PATCH(
        "/api/v1/admin/users/{user_id}",
        {
          params: { path: { user_id: selected.id } },
          body,
        },
      );
      setResult(error, error ? null : "用户已保存");
      if (data) selectUser(data);
      if (!error) loadUsers();
    } catch (error) {
      setResult(error, null);
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <AdminGrid
      title="用户管理"
      onRefresh={loadUsers}
      refreshing={isRefreshing}
      list={
        <>
          <input
            className={inputClassName}
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            onKeyDown={(event) => event.key === "Enter" && loadUsers()}
            placeholder="搜索用户名、邮箱或姓名"
          />
          <ItemList>
            {users.map((user) => (
              <ListButton
                key={user.id}
                active={selected?.id === user.id}
                title={user.username}
                meta={`${ROLE_MAP[user.role]} · #${user.id}`}
                onClick={() => selectUser(user)}
              />
            ))}
          </ItemList>
        </>
      }
    >
      {selected ? (
        <form onSubmit={saveUser} className="grid gap-4">
          <FormHeader
            title={selected.username}
            subtitle={`用户 #${selected.id}`}
          />
          <div className="grid gap-4 md:grid-cols-2">
            <Field label="用户名">
              <input
                className={inputClassName}
                value={form.username}
                onChange={(event) =>
                  setForm({ ...form, username: event.target.value })
                }
              />
            </Field>
            <Field label="邮箱">
              <input
                className={inputClassName}
                value={form.email}
                onChange={(event) =>
                  setForm({ ...form, email: event.target.value })
                }
              />
            </Field>
          </div>
          <Field label="头像 URL">
            <input
              className={inputClassName}
              value={form.avatar_uri}
              onChange={(event) =>
                setForm({ ...form, avatar_uri: event.target.value })
              }
            />
          </Field>
          <Field label="角色">
            <select
              className={selectClassName}
              value={form.role}
              onChange={(event) =>
                setForm({ ...form, role: event.target.value as Role })
              }
            >
              {ROLE_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </Field>
          <Field label="简介">
            <textarea
              className={textareaClassName}
              value={form.description}
              onChange={(event) =>
                setForm({ ...form, description: event.target.value })
              }
            />
          </Field>
          <PrimaryButton type="submit" loading={isSaving}>
            <Save size={16} /> 保存用户
          </PrimaryButton>
        </form>
      ) : (
        <PickPlaceholder label="从左侧选择用户" />
      )}
    </AdminGrid>
  );
}

function ClubsAdmin() {
  const { isRefreshing, refreshStart, refreshEnd, setResult } =
    React.useContext(RefreshContext);
  const [clubs, setClubs] = useState<ClubInfo[]>([]);
  const [search, setSearch] = useState("");
  const [selected, setSelected] = useState<ClubInfo | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [form, setForm] = useState({
    summary: "",
    description: "",
    logo_uri: "",
    star_level: "" as ClubStarLevel | "",
    status: "" as ClubStatus | "",
  });

  const loadClubs = async () => {
    refreshStart();
    try {
      const { data, error } = await client.GET("/api/v1/admin/clubs/", {
        params: { query: { size: 50, search: search || undefined } },
      });
      if (error) setResult(error, null);
      setClubs(data?.items || []);
    } catch (error) {
      setResult(error, null);
    } finally {
      refreshEnd();
    }
  };

  useEffect(() => {
    loadClubs();
  }, []);

  const selectClub = (club: ClubInfo) => {
    setSelected(club);
    setForm({
      summary: club.summary || "",
      description: club.description || "",
      logo_uri: club.logo_uri || "",
      star_level: club.star_level,
      status: club.status,
    });
  };

  const saveClub = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!selected) return;
    setIsSaving(true);
    const body: AdminClubUpdate = {
      summary: nullableText(form.summary),
      description: nullableText(form.description),
      logo_uri: nullableText(form.logo_uri),
      star_level: form.star_level || null,
      status: form.status || null,
    };
    try {
      const { data, error } = await client.PATCH(
        "/api/v1/admin/clubs/{club_id}",
        {
          params: { path: { club_id: selected.id } },
          body,
        },
      );
      setResult(error, error ? null : "社团已保存");
      if (data) selectClub(data);
      if (!error) loadClubs();
    } catch (error) {
      setResult(error, null);
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <AdminGrid
      title="社团管理"
      onRefresh={loadClubs}
      refreshing={isRefreshing}
      list={
        <>
          <input
            className={inputClassName}
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            onKeyDown={(event) => event.key === "Enter" && loadClubs()}
            placeholder="搜索社团"
          />
          <ItemList>
            {clubs.map((club) => (
              <ListButton
                key={club.id}
                active={selected?.id === club.id}
                title={club.name}
                meta={`${CLUB_STATUS_MAP[club.status]} · #${club.id}`}
                onClick={() => selectClub(club)}
              />
            ))}
          </ItemList>
        </>
      }
    >
      {selected ? (
        <form onSubmit={saveClub} className="grid gap-4">
          <FormHeader title={selected.name} subtitle={`社团 #${selected.id}`} />
          <Field label="简介">
            <input
              className={inputClassName}
              value={form.summary}
              onChange={(event) =>
                setForm({ ...form, summary: event.target.value })
              }
            />
          </Field>
          <Field label="详细介绍">
            <textarea
              className={textareaClassName}
              value={form.description}
              onChange={(event) =>
                setForm({ ...form, description: event.target.value })
              }
            />
          </Field>
          <Field label="Logo URL">
            <input
              className={inputClassName}
              value={form.logo_uri}
              onChange={(event) =>
                setForm({ ...form, logo_uri: event.target.value })
              }
            />
          </Field>
          <div className="grid gap-4 md:grid-cols-2">
            <Field label="星级">
              <select
                className={selectClassName}
                value={form.star_level}
                onChange={(event) =>
                  setForm({
                    ...form,
                    star_level: event.target.value as ClubStarLevel,
                  })
                }
              >
                {STAR_LEVEL_OPTIONS.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </Field>
            <Field label="状态">
              <select
                className={selectClassName}
                value={form.status}
                onChange={(event) =>
                  setForm({ ...form, status: event.target.value as ClubStatus })
                }
              >
                {CLUB_STATUS_OPTIONS.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </Field>
          </div>
          <PrimaryButton type="submit" loading={isSaving}>
            <Save size={16} /> 保存社团
          </PrimaryButton>
        </form>
      ) : (
        <PickPlaceholder label="从左侧选择社团" />
      )}
    </AdminGrid>
  );
}

function TermsAdmin() {
  const { isRefreshing, refreshStart, refreshEnd, setResult } =
    React.useContext(RefreshContext);
  const [terms, setTerms] = useState<AcademicTerm[]>([]);
  const [selected, setSelected] = useState<AcademicTerm | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [form, setForm] = useState({
    term_name: "",
    start_date: "",
    end_date: "",
    is_current: false,
  });

  const loadTerms = async () => {
    refreshStart();
    try {
      const { data, error } = await client.GET(
        "/api/v1/admin/academic-terms/",
        {
          params: { query: { size: 100 } },
        },
      );
      if (error) setResult(error, null);
      setTerms(data?.items || []);
    } catch (error) {
      setResult(error, null);
    } finally {
      refreshEnd();
    }
  };

  useEffect(() => {
    loadTerms();
  }, []);

  const selectTerm = (term: AcademicTerm) => {
    setSelected(term);
    setForm({
      term_name: term.term_name || "",
      start_date: term.start_date,
      end_date: term.end_date,
      is_current: term.is_current,
    });
  };

  const resetCreate = () => {
    setSelected(null);
    setForm({ term_name: "", start_date: "", end_date: "", is_current: false });
  };

  const saveTerm = async (event: React.FormEvent) => {
    event.preventDefault();
    setIsSaving(true);
    try {
      if (selected) {
        const body: AcademicTermUpdate = {
          term_name: nullableText(form.term_name),
          start_date: form.start_date || null,
          end_date: form.end_date || null,
        };
        const { data, error } = await client.PATCH(
          "/api/v1/admin/academic-terms/{term_id}",
          { params: { path: { term_id: selected.id } }, body },
        );
        setResult(error, error ? null : "学期已保存");
        if (data) selectTerm(data);
      } else {
        const { data, error } = await client.POST(
          "/api/v1/admin/academic-terms/",
          {
            body: {
              term_name: nullableText(form.term_name),
              start_date: form.start_date,
              end_date: form.end_date,
              is_current: form.is_current,
            },
          },
        );
        setResult(error, error ? null : "学期已创建");
        if (data) selectTerm(data);
      }
      loadTerms();
    } catch (error) {
      setResult(error, null);
    } finally {
      setIsSaving(false);
    }
  };

  const setCurrent = async (term: AcademicTerm) => {
    const { data, error } = await client.POST(
      "/api/v1/admin/academic-terms/{term_id}/set-current",
      { params: { path: { term_id: term.id } } },
    );
    setResult(error, error ? null : "已设置当前学期");
    if (data) selectTerm(data);
    loadTerms();
  };

  const deleteTerm = async (term: AcademicTerm) => {
    if (!window.confirm(`确认删除 ${term.term_name}？`)) return;
    const { error } = await client.DELETE(
      "/api/v1/admin/academic-terms/{term_id}",
      {
        params: { path: { term_id: term.id } },
      },
    );
    setResult(error, error ? null : "学期已删除");
    if (!error) resetCreate();
    loadTerms();
  };

  return (
    <AdminGrid
      title="学期管理"
      onRefresh={loadTerms}
      refreshing={isRefreshing}
      list={
        <>
          <SecondaryButton type="button" onClick={resetCreate}>
            新建学期
          </SecondaryButton>
          <ItemList>
            {terms.map((term) => (
              <ListButton
                key={term.id}
                active={selected?.id === term.id}
                title={term.term_name}
                meta={`${formatDate(term.start_date)} - ${formatDate(term.end_date)}`}
                badge={term.is_current ? "当前" : undefined}
                onClick={() => selectTerm(term)}
              />
            ))}
          </ItemList>
        </>
      }
    >
      <form onSubmit={saveTerm} className="grid gap-4">
        <FormHeader
          title={selected ? selected.term_name : "新建学期"}
          subtitle={selected ? `学期 #${selected.id}` : "填写日期后创建"}
        />
        <Field label="学期名称">
          <input
            className={inputClassName}
            value={form.term_name}
            onChange={(event) =>
              setForm({ ...form, term_name: event.target.value })
            }
          />
        </Field>
        <div className="grid gap-4 md:grid-cols-2">
          <Field label="开始日期">
            <input
              className={inputClassName}
              type="date"
              value={form.start_date}
              onChange={(event) =>
                setForm({ ...form, start_date: event.target.value })
              }
              required
            />
          </Field>
          <Field label="结束日期">
            <input
              className={inputClassName}
              type="date"
              value={form.end_date}
              onChange={(event) =>
                setForm({ ...form, end_date: event.target.value })
              }
              required
            />
          </Field>
        </div>
        {!selected && (
          <label className="flex items-center gap-2 text-sm font-semibold text-content">
            <input
              type="checkbox"
              checked={form.is_current}
              onChange={(event) =>
                setForm({ ...form, is_current: event.target.checked })
              }
            />
            创建后设为当前学期
          </label>
        )}
        <div className="flex flex-wrap gap-2">
          <PrimaryButton type="submit" loading={isSaving}>
            <Save size={16} /> {selected ? "保存学期" : "创建学期"}
          </PrimaryButton>
          {selected && (
            <>
              <SecondaryButton
                type="button"
                onClick={() => setCurrent(selected)}
              >
                设为当前
              </SecondaryButton>
              <button
                type="button"
                onClick={() => deleteTerm(selected)}
                className="inline-flex items-center gap-2 rounded-md border border-tone-danger-edge bg-tone-danger-bg px-4 py-2.5 text-sm font-semibold text-tone-danger-fg hover:bg-tone-danger-bg-hover"
              >
                <Trash2 size={16} /> 删除
              </button>
            </>
          )}
        </div>
      </form>
    </AdminGrid>
  );
}

function ActivitiesAdmin() {
  const { isRefreshing, refreshStart, refreshEnd, setResult } =
    React.useContext(RefreshContext);
  const [items, setItems] = useState<GeneralActivity[]>([]);
  const [selected, setSelected] = useState<GeneralActivity | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [form, setForm] = useState({
    name: "",
    description: "",
    level: "large" as GeneralActivityLevel,
    starts_at: "",
    ends_at: "",
    poster_uri: "",
    article_url: "",
  });

  const loadItems = async () => {
    refreshStart();
    try {
      const { data, error } = await client.GET(
        "/api/v1/admin/general-activities/",
        {
          params: { query: { size: 100 } },
        },
      );
      if (error) setResult(error, null);
      setItems(data?.items || []);
    } catch (error) {
      setResult(error, null);
    } finally {
      refreshEnd();
    }
  };

  useEffect(() => {
    loadItems();
  }, []);

  const selectItem = (item: GeneralActivity) => {
    setSelected(item);
    setForm({
      name: item.name || "",
      description: item.description || "",
      level: item.level,
      starts_at: toDateTimeLocalValue(item.starts_at),
      ends_at: toDateTimeLocalValue(item.ends_at),
      poster_uri: item.poster_uri || "",
      article_url: item.article_url || "",
    });
  };

  const resetCreate = () => {
    setSelected(null);
    setForm({
      name: "",
      description: "",
      level: "large",
      starts_at: "",
      ends_at: "",
      poster_uri: "",
      article_url: "",
    });
  };

  const buildBody = () => ({
    name: form.name,
    description: form.description,
    level: form.level,
    starts_at: form.starts_at ? fromDateTimeLocalValue(form.starts_at) : null,
    ends_at: form.ends_at ? fromDateTimeLocalValue(form.ends_at) : null,
    poster_uri: nullableText(form.poster_uri),
    article_url: nullableText(form.article_url),
  });

  const saveItem = async (event: React.FormEvent) => {
    event.preventDefault();
    setIsSaving(true);
    try {
      if (selected) {
        const { data, error } = await client.PATCH(
          "/api/v1/admin/general-activities/{activity_id}",
          { params: { path: { activity_id: selected.id } }, body: buildBody() },
        );
        setResult(error, error ? null : "大型活动已保存");
        if (data) selectItem(data);
      } else {
        const { data, error } = await client.POST(
          "/api/v1/admin/general-activities/",
          {
            body: buildBody(),
          },
        );
        setResult(error, error ? null : "大型活动已创建");
        if (data) selectItem(data);
      }
      loadItems();
    } catch (error) {
      setResult(error, null);
    } finally {
      setIsSaving(false);
    }
  };

  const deleteItem = async (item: GeneralActivity) => {
    if (!window.confirm(`确认删除 ${item.name}？`)) return;
    const { error } = await client.DELETE(
      "/api/v1/admin/general-activities/{activity_id}",
      { params: { path: { activity_id: item.id } } },
    );
    setResult(error, error ? null : "大型活动已删除");
    if (!error) resetCreate();
    loadItems();
  };

  return (
    <AdminGrid
      title="大型活动管理"
      onRefresh={loadItems}
      refreshing={isRefreshing}
      list={
        <>
          <SecondaryButton
            type="button"
            onClick={resetCreate}
            className="w-full whitespace-nowrap"
          >
            新建大型活动
          </SecondaryButton>
          <ItemList>
            {items.map((item) => (
              <ListButton
                key={item.id}
                active={selected?.id === item.id}
                title={item.name}
                meta={`${ACTIVITY_LEVEL_MAP[item.level]} · ${formatDate(item.starts_at || item.created_at)}`}
                onClick={() => selectItem(item)}
              />
            ))}
          </ItemList>
        </>
      }
    >
      <form onSubmit={saveItem} className="grid min-w-0 gap-4">
        <FormHeader
          title={selected ? selected.name : "新建大型活动"}
          subtitle={
            selected ? `活动 #${selected.id}` : "用于首页展板和活动日历"
          }
        />
        <Field label="活动名称">
          <input
            className={inputClassName}
            value={form.name}
            onChange={(event) => setForm({ ...form, name: event.target.value })}
            required
          />
        </Field>
        <Field label="活动级别">
          <select
            className={selectClassName}
            value={form.level}
            onChange={(event) =>
              setForm({
                ...form,
                level: event.target.value as GeneralActivityLevel,
              })
            }
          >
            {ACTIVITY_LEVEL_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </Field>
        <div className="grid min-w-0 gap-4 md:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
          <Field label="开始时间">
            <input
              className={inputClassName}
              type="datetime-local"
              value={form.starts_at}
              onChange={(event) =>
                setForm({ ...form, starts_at: event.target.value })
              }
            />
          </Field>
          <Field label="结束时间">
            <input
              className={inputClassName}
              type="datetime-local"
              value={form.ends_at}
              onChange={(event) =>
                setForm({ ...form, ends_at: event.target.value })
              }
            />
          </Field>
        </div>
        <FileUploadField
          label="活动海报"
          scene="activity_poster"
          value={form.poster_uri}
          onChange={(poster_uri) => setForm({ ...form, poster_uri })}
          accept="image/*"
          resizeImage
          maxWidth={1600}
          maxHeight={1200}
          quality={0.86}
          hint="上传后会自动压缩并填入展板海报。"
        />
        <Field label="公众号文章链接">
          <input
            className={inputClassName}
            value={form.article_url}
            onChange={(event) =>
              setForm({ ...form, article_url: event.target.value })
            }
          />
        </Field>
        <Field label="活动描述">
          <textarea
            className={textareaClassName}
            value={form.description}
            onChange={(event) =>
              setForm({ ...form, description: event.target.value })
            }
            required
          />
        </Field>
        <div className="flex flex-wrap gap-2">
          <PrimaryButton type="submit" loading={isSaving}>
            <Save size={16} /> {selected ? "保存活动" : "创建活动"}
          </PrimaryButton>
          {selected && (
            <button
              type="button"
              onClick={() => deleteItem(selected)}
              className="inline-flex items-center gap-2 rounded-md border border-tone-danger-edge bg-tone-danger-bg px-4 py-2.5 text-sm font-semibold text-tone-danger-fg hover:bg-tone-danger-bg-hover"
            >
              <Trash2 size={16} /> 删除
            </button>
          )}
        </div>
      </form>
    </AdminGrid>
  );
}

function AnnouncementsAdmin() {
  const { isRefreshing, refreshStart, refreshEnd, setResult } =
    React.useContext(RefreshContext);
  const [items, setItems] = useState<Announcement[]>([]);
  const [selected, setSelected] = useState<Announcement | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [form, setForm] = useState({
    title: "",
    body: "",
    link_url: "",
    starts_at: "",
    ends_at: "",
    is_active: true,
  });

  const loadItems = async () => {
    refreshStart();
    try {
      const { data, error } = await client.GET("/api/v1/admin/announcements/", {
        params: { query: { size: 100, active_only: false } },
      });
      if (error) setResult(error, null);
      setItems(data?.items || []);
    } catch (error) {
      setResult(error, null);
    } finally {
      refreshEnd();
    }
  };

  useEffect(() => {
    loadItems();
  }, []);

  const selectItem = (item: Announcement) => {
    setSelected(item);
    setForm({
      title: item.title || "",
      body: item.body || "",
      link_url: item.link_url || "",
      starts_at: toDateTimeLocalValue(item.starts_at),
      ends_at: toDateTimeLocalValue(item.ends_at),
      is_active: item.is_active,
    });
  };

  const resetCreate = () => {
    setSelected(null);
    setForm({
      title: "",
      body: "",
      link_url: "",
      starts_at: "",
      ends_at: "",
      is_active: true,
    });
  };

  const buildBody = () => ({
    title: form.title,
    body: form.body,
    link_url: nullableText(form.link_url),
    starts_at: form.starts_at ? fromDateTimeLocalValue(form.starts_at) : null,
    ends_at: form.ends_at ? fromDateTimeLocalValue(form.ends_at) : null,
    is_active: form.is_active,
  });

  const saveItem = async (event: React.FormEvent) => {
    event.preventDefault();
    setIsSaving(true);
    try {
      if (selected) {
        const { data, error } = await client.PATCH(
          "/api/v1/admin/announcements/{announcement_id}",
          {
            params: { path: { announcement_id: selected.id } },
            body: buildBody(),
          },
        );
        setResult(error, error ? null : "公告已保存");
        if (data) selectItem(data);
      } else {
        const { data, error } = await client.POST(
          "/api/v1/admin/announcements/",
          {
            body: buildBody(),
          },
        );
        setResult(error, error ? null : "公告已创建");
        if (data) selectItem(data);
      }
      loadItems();
    } catch (error) {
      setResult(error, null);
    } finally {
      setIsSaving(false);
    }
  };

  const deleteItem = async (item: Announcement) => {
    if (!window.confirm(`确认删除 ${item.title}？`)) return;
    const { error } = await client.DELETE(
      "/api/v1/admin/announcements/{announcement_id}",
      {
        params: { path: { announcement_id: item.id } },
      },
    );
    setResult(error, error ? null : "公告已删除");
    if (!error) resetCreate();
    loadItems();
  };

  return (
    <AdminGrid
      title="公告管理"
      onRefresh={loadItems}
      refreshing={isRefreshing}
      list={
        <>
          <SecondaryButton type="button" onClick={resetCreate}>
            新建公告
          </SecondaryButton>
          <ItemList>
            {items.map((item) => (
              <ListButton
                key={item.id}
                active={selected?.id === item.id}
                title={item.title}
                meta={formatDate(item.created_at)}
                badge={item.is_active ? "启用" : "停用"}
                onClick={() => selectItem(item)}
              />
            ))}
          </ItemList>
        </>
      }
    >
      <form onSubmit={saveItem} className="grid gap-4">
        <FormHeader
          title={selected ? selected.title : "新建公告"}
          subtitle={selected ? `公告 #${selected.id}` : "显示在首页公告栏"}
        />
        <Field label="标题">
          <input
            className={inputClassName}
            value={form.title}
            onChange={(event) =>
              setForm({ ...form, title: event.target.value })
            }
            required
          />
        </Field>
        <Field label="正文">
          <textarea
            className={textareaClassName}
            value={form.body}
            onChange={(event) => setForm({ ...form, body: event.target.value })}
            required
          />
        </Field>
        <Field label="链接">
          <input
            className={inputClassName}
            value={form.link_url}
            onChange={(event) =>
              setForm({ ...form, link_url: event.target.value })
            }
          />
        </Field>
        <div className="grid gap-4 md:grid-cols-2">
          <Field label="开始展示">
            <input
              className={inputClassName}
              type="datetime-local"
              value={form.starts_at}
              onChange={(event) =>
                setForm({ ...form, starts_at: event.target.value })
              }
            />
          </Field>
          <Field label="结束展示">
            <input
              className={inputClassName}
              type="datetime-local"
              value={form.ends_at}
              onChange={(event) =>
                setForm({ ...form, ends_at: event.target.value })
              }
            />
          </Field>
        </div>
        <label className="flex items-center gap-2 text-sm font-semibold text-content">
          <input
            type="checkbox"
            checked={form.is_active}
            onChange={(event) =>
              setForm({ ...form, is_active: event.target.checked })
            }
          />
          启用公告
        </label>
        <div className="flex flex-wrap gap-2">
          <PrimaryButton type="submit" loading={isSaving}>
            <Save size={16} /> {selected ? "保存公告" : "创建公告"}
          </PrimaryButton>
          {selected && (
            <button
              type="button"
              onClick={() => deleteItem(selected)}
              className="inline-flex items-center gap-2 rounded-md border border-tone-danger-edge bg-tone-danger-bg px-4 py-2.5 text-sm font-semibold text-tone-danger-fg hover:bg-tone-danger-bg-hover"
            >
              <Trash2 size={16} /> 删除
            </button>
          )}
        </div>
      </form>
    </AdminGrid>
  );
}

function AdminGrid({
  title,
  list,
  children,
  refreshing,
  onRefresh,
}: {
  title: string;
  list: React.ReactNode;
  children: React.ReactNode;
  refreshing: boolean;
  onRefresh: () => void;
}) {
  return (
    <div className="grid min-w-0 gap-5 xl:grid-cols-[320px_minmax(0,1fr)]">
      <div className="grid min-w-0 content-start gap-3 self-start">
        <div className="flex items-center justify-between">
          <h2 className="font-display text-lg font-bold">{title}</h2>
          <button
            type="button"
            onClick={onRefresh}
            disabled={refreshing}
            className="inline-flex h-9 w-9 items-center justify-center rounded-md border border-edge text-content-muted hover:bg-surface-sunken disabled:opacity-50"
            aria-label="刷新"
          >
            <RefreshCw size={15} className={cn(refreshing && "animate-spin")} />
          </button>
        </div>
        {list}
      </div>
      <div className="min-h-[420px] min-w-0 rounded-md border border-edge bg-surface-sunken p-4">
        {children}
      </div>
    </div>
  );
}

function ItemList({ children }: { children: React.ReactNode }) {
  return (
    <div className="max-h-[620px] space-y-2 overflow-y-auto overflow-x-hidden pr-1">
      {children}
    </div>
  );
}

function ListButton({
  title,
  meta,
  badge,
  active,
  onClick,
}: {
  key?: React.Key;
  title: string;
  meta?: string;
  badge?: string;
  active?: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "w-full min-w-0 rounded-md border p-3 text-left transition",
        active
          ? "border-content bg-surface"
          : "border-edge bg-surface hover:border-edge-strong",
      )}
    >
      <div className="flex min-w-0 items-center justify-between gap-2">
        <p className="min-w-0 truncate text-sm font-semibold text-content">
          {title}
        </p>
        {badge && <Badge tone="primary">{badge}</Badge>}
      </div>
      {meta && <p className="mt-1 truncate text-xs text-content-muted">{meta}</p>}
    </button>
  );
}

function FormHeader({ title, subtitle }: { title: string; subtitle: string }) {
  return (
    <div className="min-w-0 border-b border-edge pb-3">
      <h3 className="break-words font-display text-xl font-bold text-content">
        {title}
      </h3>
      <p className="break-words text-sm text-content-muted">{subtitle}</p>
    </div>
  );
}

function PickPlaceholder({ label }: { label: string }) {
  return (
    <div className="flex min-h-[360px] items-center justify-center rounded-md border border-dashed border-edge bg-surface text-sm font-semibold text-content-muted">
      {label}
    </div>
  );
}
