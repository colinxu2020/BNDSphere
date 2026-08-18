import React, { useEffect, useState } from "react";
import { Save, Trash2 } from "@/src/components/ui/Icons";
import { client } from "../../api/client";
import type { components } from "../../api/schema";
import { ACTIVITY_LEVEL_MAP, ACTIVITY_LEVEL_OPTIONS } from "../../lib/labels";
import {
  formatDate,
  fromDateTimeLocalValue,
  nullableText,
  toDateTimeLocalValue,
} from "../../lib/format";
import {
  Field,
  PrimaryButton,
  SecondaryButton,
  inputClassName,
  selectClassName,
  textareaClassName,
} from "../../components/ui/AppPrimitives";
import { FileUploadField } from "../../components/ui/FileUploadField";
import { AdminGrid, ItemList, ListButton, FormHeader } from "./primitives";
import { useAdminContext } from "./context";

type GeneralActivity = components["schemas"]["GeneralActivityInfo"];
type GeneralActivityLevel = components["schemas"]["GeneralActivityLevelEnum"];

export function ActivitiesAdmin() {
  const { isRefreshing, refreshStart, refreshEnd, setResult } =
    useAdminContext();
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
