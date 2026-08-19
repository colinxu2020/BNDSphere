/**
 * Design-system specimen — DEVELOPMENT ONLY.
 *
 * Registered only when `import.meta.env.DEV` is true, behind a dynamic import,
 * so Vite tree-shakes this module out of the production bundle entirely rather
 * than merely making the URL unreachable. See App.tsx.
 *
 * Purpose: make the Gate 4 manual matrix tractable. Reviewing every token, tone,
 * category and component state across macOS / Windows / iOS / Android x
 * light / dark is one screenshot per combination here, instead of navigating
 * fifteen pages eight times.
 *
 * Interaction states are presented in FORCED form — a static element styled with
 * the same classes the real state applies — because a screenshot cannot be
 * relied on to catch a real :hover or :focus. The live control sits beside the
 * forced one so the two can be compared.
 */

import { Inbox } from "@/src/components/ui/Icons";
import { SectionTitle, Surface } from "../components/ui/AppPrimitives";
import { ActivityLevelChip } from "../components/ui/ActivityCard";
import { CategoryChip, categorySpine } from "../components/ui/CategoryChip";
import { StarLevel, StarLevelCompact } from "../components/ui/StarLevel";

const TONES = [
  ["neutral", "中性"],
  ["brand", "品牌 / 强调"],
  ["info", "信息状态"],
  ["success", "成功"],
  ["warning", "警告"],
  ["danger", "危险"],
] as const;

const CATEGORIES = [
  ["science", "科学"],
  ["humanity", "人文"],
  ["arts", "艺术"],
  ["sports", "体育"],
  ["business", "商业"],
  ["charity", "公益"],
  ["campus", "校园"],
  ["other", "其他"],
] as const;

/** Class strings are written out in full rather than interpolated, because
 *  Tailwind scans source as text and never sees a constructed class name. */
const TONE_CLASSES: Record<string, string> = {
  neutral: "bg-tone-neutral-bg text-tone-neutral-fg border-tone-neutral-edge",
  brand: "bg-tone-brand-bg text-tone-brand-fg border-tone-brand-edge",
  info: "bg-tone-info-bg text-tone-info-fg border-tone-info-edge",
  success: "bg-tone-success-bg text-tone-success-fg border-tone-success-edge",
  warning: "bg-tone-warning-bg text-tone-warning-fg border-tone-warning-edge",
  danger: "bg-tone-danger-bg text-tone-danger-fg border-tone-danger-edge",
};

const STAR_LEVELS = [
  "none",
  "one_star",
  "two_star",
  "three_star",
  "four_star",
  "five_star",
  "honorary",
] as const;

const TYPE_SCALE = [
  ["text-xs", "文本 xs"],
  ["text-sm", "文本 sm"],
  ["text-base", "文本 base"],
  ["text-lg", "文本 lg"],
  ["text-xl", "文本 xl"],
  ["text-2xl", "标题 2xl"],
  ["text-3xl", "标题 3xl"],
  ["text-4xl", "标题 4xl"],
  ["text-5xl", "标题 5xl"],
] as const;

const TYPE_CLASSES: Record<string, string> = {
  "text-xs": "text-xs",
  "text-sm": "text-sm",
  "text-base": "text-base",
  "text-lg": "text-lg",
  "text-xl": "text-xl",
  "text-2xl": "text-2xl",
  "text-3xl": "text-3xl",
  "text-4xl": "text-4xl",
  "text-5xl": "text-5xl",
};

/** Mixed CN / Latin / numeric, to expose metric mismatches between the Latin
 *  face and the CJK fallback in the same line. */
const MIXED_SAMPLE = "十一学校 BNDSphere 社团 2026 年第 3 期 · 128 名成员";

function Section({
  title,
  note,
  children,
}: {
  title: string;
  note?: string;
  children: React.ReactNode;
}) {
  return (
    <section className="border-edge bg-surface rounded-md border p-6">
      <h2 className="text-content font-display text-xl font-bold">{title}</h2>
      {note && <p className="text-content-muted mt-1 text-sm">{note}</p>}
      <div className="mt-5">{children}</div>
    </section>
  );
}

function Swatch({ label, className }: { label: string; className: string }) {
  return (
    <div className="flex flex-col gap-1">
      <div className={`border-edge h-14 rounded-md border ${className}`} />
      <code className="text-content-subtle text-xs">{label}</code>
    </div>
  );
}

export default function Specimen() {
  return (
    <div className="bg-surface-sunken min-h-screen p-6">
      <div className="mx-auto flex max-w-6xl flex-col gap-6">
        <header>
          <p className="text-brand text-xs font-bold tracking-wider uppercase">
            Gate 4 · specimen
          </p>
          <h1 className="text-content font-display text-3xl font-bold">
            设计系统样张
          </h1>
          <p className="text-content-muted mt-1">
            开发环境专用页面。切换系统的浅色 / 深色外观以校验两套配色。
          </p>
        </header>

        <Section
          title="表面与文本 Surfaces & content"
          note="语义化令牌，深浅两套配色由 prefers-color-scheme 切换。"
        >
          <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
            <Swatch label="bg-surface" className="bg-surface" />
            <Swatch label="bg-surface-raised" className="bg-surface-raised" />
            <Swatch label="bg-surface-sunken" className="bg-surface-sunken" />
            <Swatch label="bg-surface-hover" className="bg-surface-hover" />
            <Swatch label="bg-brand" className="bg-brand" />
            <Swatch label="bg-brand-hover" className="bg-brand-hover" />
            <Swatch label="bg-brand-subtle" className="bg-brand-subtle" />
            <Swatch label="bg-edge-strong" className="bg-edge-strong" />
          </div>
          <div className="mt-5 flex flex-col gap-1">
            <p className="text-content">text-content · 主要文本</p>
            <p className="text-content-muted">text-content-muted · 次要文本</p>
            <p className="text-content-subtle">
              text-content-subtle · 辅助文本
            </p>
            <p className="bg-brand text-brand-on inline-block rounded-md px-2 py-1">
              text-brand-on · 品牌底色上的文本
            </p>
          </div>
        </Section>

        <Section
          title="状态色调 Status tones"
          note="neutral · brand · info · success · warning · danger。brand 表示身份与强调，info 表示系统信息状态 —— 两者语义不同，即使色相相近。"
        >
          <div className="flex flex-wrap gap-3">
            {TONES.map(([key, label]) => (
              <span
                key={key}
                className={`inline-flex items-center rounded-md border px-2.5 py-1 text-xs font-bold ${TONE_CLASSES[key]}`}
              >
                {label} · {key}
              </span>
            ))}
          </div>
          <div className="mt-4 flex flex-col gap-2">
            {TONES.map(([key, label]) => (
              <div
                key={key}
                className={`rounded-md border p-4 text-sm font-medium ${TONE_CLASSES[key]}`}
              >
                {label}：操作未能完成，请稍后重试。Request failed with status 422.
              </div>
            ))}
          </div>
        </Section>

        <Section
          title="社团类别 Club categories"
          note="八类固定色相，明度亦有差异，因此不依赖色相辨识即可区分；仅用于小元素。其他 保持中性。"
        >
          <div className="flex flex-wrap gap-3">
            {CATEGORIES.map(([key]) => (
              <CategoryChip key={key} category={key} size="lg" />
            ))}
          </div>
          <div className="mt-3 flex flex-wrap gap-2">
            {CATEGORIES.map(([key]) => (
              <CategoryChip key={key} category={key} size="sm" />
            ))}
          </div>
        </Section>

        <Section
          title="社团星级 Star levels"
          note="单一等级序列:无星级 → 一星 → … → 五星 → 荣誉社团。荣誉社团为该序列的最高级,以五星加印章表示,而非第六颗星。每种呈现都保留文字等级 —— 星形与印章从不单独承载语义。"
        >
          <div className="flex flex-col gap-3">
            <div className="flex flex-wrap items-center gap-3">
              {STAR_LEVELS.map((level) => (
                <StarLevel key={level} level={level} size="lg" />
              ))}
            </div>
            <div className="flex flex-wrap items-center gap-2">
              {STAR_LEVELS.map((level) => (
                <StarLevel key={level} level={level} size="sm" />
              ))}
            </div>
            <div className="flex flex-wrap items-center gap-2">
              {STAR_LEVELS.filter((l) => l !== "none").map((level) => (
                <StarLevel
                  key={level}
                  level={level}
                  size="md"
                  showLabel={false}
                />
              ))}
              <span className="text-content-muted text-sm">
                ← showLabel=false,文字等级仍以 sr-only 保留
              </span>
            </div>
            <div className="border-edge-subtle flex flex-wrap items-center gap-4 border-t pt-3">
              {STAR_LEVELS.map((level) => (
                <StarLevelCompact key={level} level={level} />
              ))}
              <span className="text-content-muted text-sm">
                ← 密集表格用的紧凑变体
              </span>
            </div>
          </div>
        </Section>

        <Section
          title="活动级别 Activity levels"
          note="校级 / 大型 / 社联 —— 活动级别是它“是什么”,因此与社团类别一样属于身份标识,而非状态色调,并使用独立色相,以免与类别色混淆。"
        >
          <div className="flex flex-wrap gap-3">
            {(["school", "large", "club_federation"] as const).map((lvl) => (
              <ActivityLevelChip key={lvl} level={lvl} />
            ))}
          </div>
        </Section>

        <Section
          title="中文排版 CJK typography"
          note="每一级字号都需在目标平台上核对行高与间距。中西文混排会暴露拉丁字体与中文回退字体之间的度量差异。"
        >
          <div className="flex flex-col gap-3">
            {TYPE_SCALE.map(([cls, label]) => (
              <div key={cls} className="border-edge-subtle border-b pb-2">
                <code className="text-content-subtle text-xs">{cls}</code>
                <p className={`text-content ${TYPE_CLASSES[cls]}`}>
                  {label} · 社团活动与星级评价
                </p>
              </div>
            ))}
          </div>
          <div className="mt-5 flex flex-col gap-2">
            <p className="text-content text-base">{MIXED_SAMPLE}</p>
            <p className="text-content font-display text-2xl font-bold">
              {MIXED_SAMPLE}
            </p>
            <p className="text-content-muted text-sm">
              上面一行为 font-sans，下面一行为 font-display。Space Grotesk
              不含中文字形，因此中文部分回退到 CJK 字体族 —— 这是预期行为。
            </p>
          </div>
        </Section>

        <Section
          title="交互状态 Interaction states"
          note="每组左侧为真实控件，右侧为强制呈现的静态样式：截图无法可靠捕捉 :hover 或 :focus，因此两者并列比对。"
        >
          <div className="flex flex-col gap-6">
            <div>
              <p className="text-content-muted mb-2 text-sm font-semibold">
                主按钮 · 真实 / rest · hover(强制) · focus(强制) · disabled
              </p>
              <div className="flex flex-wrap items-center gap-3">
                <button
                  type="button"
                  className="bg-brand text-brand-on hover:bg-brand-hover focus-visible:ring-brand-strong/40 inline-flex items-center rounded-md px-5 py-3 font-semibold transition-all focus-visible:ring-4 active:scale-[0.98]"
                >
                  真实按钮 Live
                </button>
                <span className="bg-brand text-brand-on inline-flex items-center rounded-md px-5 py-3 font-semibold">
                  rest
                </span>
                <span className="bg-brand-hover text-brand-on inline-flex items-center rounded-md px-5 py-3 font-semibold">
                  hover(强制)
                </span>
                <span className="bg-brand text-brand-on ring-brand-strong/40 inline-flex items-center rounded-md px-5 py-3 font-semibold ring-4">
                  focus(强制)
                </span>
                <button
                  type="button"
                  disabled
                  className="bg-brand text-brand-on inline-flex items-center rounded-md px-5 py-3 font-semibold disabled:cursor-not-allowed disabled:opacity-70"
                >
                  disabled
                </button>
              </div>
            </div>

            <div>
              <p className="text-content-muted mb-2 text-sm font-semibold">
                次按钮 / 表面悬停
              </p>
              <div className="flex flex-wrap items-center gap-3">
                <button
                  type="button"
                  className="bg-surface-sunken border-edge text-content hover:bg-surface-hover inline-flex items-center rounded-md border px-4 py-2.5 font-semibold transition-all active:scale-[0.98]"
                >
                  真实按钮 Live
                </button>
                <span className="bg-surface-sunken border-edge text-content inline-flex items-center rounded-md border px-4 py-2.5 font-semibold">
                  rest
                </span>
                <span className="bg-surface-hover border-edge text-content inline-flex items-center rounded-md border px-4 py-2.5 font-semibold">
                  hover(强制)
                </span>
              </div>
            </div>

            <div>
              <p className="text-content-muted mb-2 text-sm font-semibold">
                输入框 · rest · focus(强制) · 错误 · disabled
              </p>
              <div className="grid gap-3 md:grid-cols-2">
                <input
                  className="bg-surface-sunken border-edge text-content placeholder:text-content-subtle focus:border-brand focus:ring-brand-strong/20 w-full rounded-md border px-4 py-3 font-medium outline-none focus:ring-2"
                  placeholder="真实输入框 · 点击以查看 focus"
                />
                <input
                  className="bg-surface-sunken border-brand text-content ring-brand-strong/20 w-full rounded-md border px-4 py-3 font-medium ring-2 outline-none"
                  defaultValue="focus(强制)"
                />
                <input
                  className="bg-tone-danger-bg border-tone-danger-edge text-tone-danger-fg w-full rounded-md border px-4 py-3 font-medium outline-none"
                  defaultValue="错误状态 · 名称已被占用"
                />
                <input
                  disabled
                  className="bg-surface-sunken border-edge text-content w-full rounded-md border px-4 py-3 font-medium opacity-60 outline-none"
                  defaultValue="disabled"
                />
              </div>
            </div>

            <div>
              <p className="text-content-muted mb-2 text-sm font-semibold">
                浮层与阴影 · 深色配色下阴影几乎不可见，改用边框与表面明度表达层级
              </p>
              <div className="flex flex-wrap items-start gap-4">
                <div className="border-edge bg-surface-raised w-56 rounded-md border p-3 shadow-lg">
                  <p className="text-content text-sm font-semibold">
                    菜单浮层(强制展开)
                  </p>
                  <div className="bg-edge-subtle my-2 h-px" />
                  <p className="text-content-muted text-sm">个人主页</p>
                  <p className="text-content-muted text-sm">我管理的社团</p>
                  <p className="text-tone-danger-fg text-sm font-semibold">
                    退出登录
                  </p>
                </div>
                <div className="border-edge bg-surface-raised w-56 rounded-md border p-4">
                  <p className="text-content text-sm">
                    无阴影,仅边框 —— 深色下的层级表达
                  </p>
                </div>
              </div>
            </div>
          </div>
        </Section>

        <Section
          title="图像与标识 Imagery & logos"
          note="标识为位图,需在深色表面上单独核对;用户上传的头像与海报需要一致的边框处理。"
        >
          <div className="flex flex-wrap items-center gap-6">
            <div className="border-edge bg-surface rounded-md border p-4">
              <img src="/LOGO_FULL.png" alt="BNDSphere" className="h-10" />
              <code className="text-content-subtle mt-2 block text-xs">
                on bg-surface
              </code>
            </div>
            <div className="border-edge bg-surface-sunken rounded-md border p-4">
              <img src="/LOGO_FULL.png" alt="BNDSphere" className="h-10" />
              <code className="text-content-subtle mt-2 block text-xs">
                on bg-surface-sunken
              </code>
            </div>
            <div className="border-edge bg-surface-raised flex items-center gap-3 rounded-md border p-4">
              <div className="border-edge bg-surface-sunken text-content-muted flex h-10 w-10 items-center justify-center overflow-hidden rounded-full border text-sm font-bold">
                十
              </div>
              <code className="text-content-subtle text-xs">
                avatar fallback
              </code>
            </div>
          </div>
        </Section>

        <Section
          title="键盘与动效 Keyboard & motion"
          note="用 Tab 键遍历以下控件,核对焦点样式是否可见、顺序是否合理;菜单关闭后焦点应回到触发元素。开启系统的“减弱动态效果”后,过渡应当停止。"
        >
          <div className="flex flex-wrap gap-3">
            {["第一个", "第二个", "第三个"].map((label) => (
              <button
                key={label}
                type="button"
                className="border-edge bg-surface text-content focus-visible:ring-brand-strong/40 focus-visible:border-brand rounded-md border px-4 py-2 font-semibold focus-visible:ring-4"
              >
                {label}焦点目标
              </button>
            ))}
            <a
              href="#top"
              className="text-brand focus-visible:ring-brand-strong/40 rounded-md px-2 py-2 font-semibold underline focus-visible:ring-4"
            >
              链接焦点
            </a>
          </div>
          <div className="motion-safe:animate-pulse bg-brand-subtle border-tone-brand-edge text-tone-brand-fg mt-4 rounded-md border p-3 text-sm font-semibold">
            此块使用 motion-safe:animate-pulse —— 在“减弱动态效果”下应静止。
          </div>
        </Section>

        <Section
          title="面板密度 Panel density"
          note="公共界面可以留白,工作台需要在一屏内看到更多内容并减少装饰。同一个 Surface 组件的两种密度,因此二者不会各自漂移。"
        >
          <div className="grid gap-4 md:grid-cols-2">
            <Surface>
              <SectionTitle
                icon={<Inbox size={20} />}
                title="公共界面"
                description="comfortable · p-6 md:p-8"
              />
              <p className="text-content-muted text-sm">
                用于社团主页、活动页等表达性界面。
              </p>
            </Surface>
            <Surface density="compact">
              <SectionTitle
                density="compact"
                icon={<Inbox size={16} />}
                title="工作台"
                description="compact · p-4 md:p-5"
              />
              <p className="text-content-muted text-sm">
                用于审核队列、管理控制台等操作性界面。
              </p>
            </Surface>
          </div>
        </Section>

        <Section
          title="形状与层级 Shape & elevation"
          note="卡片以硬投影表现层级 —— 没有模糊。模糊阴影在深色表面上几乎消失,而硬投影是一条画出来的边,在两套配色下都成立,也与全局 1.5px 描边一致。悬停时卡片向左上位移,像从板面上被拈起。"
        >
          <div className="grid gap-4 md:grid-cols-3">
            {(["sm", "md", "lg"] as const).map((step) => (
              <div
                key={step}
                className={`border-edge bg-surface rounded-md border p-4 ${
                  step === "sm"
                    ? "shadow-sm"
                    : step === "md"
                      ? "shadow-md"
                      : "shadow-lg"
                }`}
              >
                <code className="text-content-subtle text-xs">
                  shadow-{step}
                </code>
                <p className="text-content mt-1 text-sm font-semibold">
                  硬投影层级
                </p>
              </div>
            ))}
          </div>
          <div className="mt-5 grid gap-4 md:grid-cols-2">
            {(["science", "arts"] as const).map((cat) => (
              <div
                key={cat}
                className={`border-edge bg-surface rounded-md border border-l-4 p-4 shadow-sm transition-all hover:-translate-x-0.5 hover:-translate-y-0.5 hover:shadow-lg motion-reduce:transform-none ${categorySpine(cat)}`}
              >
                <CategoryChip category={cat} size="sm" />
                <p className="text-content mt-2 font-semibold">
                  类别脊边 · 悬停以查看位移
                </p>
                <p className="text-content-muted text-sm">
                  边而非填充,因此仍遵守“类别色仅用于小元素”的约束。
                </p>
              </div>
            ))}
          </div>
        </Section>

        <Section
          title="原始色阶 Primitive ramps"
          note="仅供参考:这些是语义令牌背后的原色阶,应用代码不应直接使用。"
        >
          <div className="grid grid-cols-6 gap-2 md:grid-cols-11">
            {[
              "bg-primary-50",
              "bg-primary-100",
              "bg-primary-200",
              "bg-primary-300",
              "bg-primary-400",
              "bg-primary-500",
              "bg-primary-600",
              "bg-primary-700",
              "bg-primary-800",
              "bg-primary-900",
              "bg-primary-950",
            ].map((c) => (
              <Swatch key={c} label={c.replace("bg-primary-", "")} className={c} />
            ))}
          </div>
          <div className="mt-3 grid grid-cols-6 gap-2 md:grid-cols-11">
            {[
              "bg-secondary-50",
              "bg-secondary-100",
              "bg-secondary-200",
              "bg-secondary-300",
              "bg-secondary-400",
              "bg-secondary-500",
              "bg-secondary-600",
              "bg-secondary-700",
              "bg-secondary-800",
              "bg-secondary-900",
              "bg-secondary-950",
            ].map((c) => (
              <Swatch
                key={c}
                label={c.replace("bg-secondary-", "")}
                className={c}
              />
            ))}
          </div>
        </Section>
      </div>
    </div>
  );
}
