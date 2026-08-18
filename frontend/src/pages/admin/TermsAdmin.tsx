import React, { useEffect, useMemo, useState } from "react";
import {
  Bell,
  CalendarDays,
  RefreshCw,
  Save,
  Shield,
  Trash2,
  Users,
} from "@/src/components/ui/Icons";
import { client } from "../../api/client";
import type { Tone } from "../../lib/tones";
import type { components } from "../../api/schema";
import {
  formatDate,
  fromDateTimeLocalValue,
  nullableText,
  toDateTimeLocalValue,
} from "../../lib/format";
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
} from "../../components/ui/AppPrimitives";
import { AdminGrid, ItemList, ListButton, FormHeader } from "./primitives";
import { useAdminContext } from "./context";

type AcademicTerm = components["schemas"]["AcademicTermInfo"];
type AcademicTermUpdate = components["schemas"]["AcademicTermUpdate"];

export function TermsAdmin() {
  const { isRefreshing, refreshStart, refreshEnd, setResult } =
    useAdminContext();
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
