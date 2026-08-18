export function stringifyBackendValue(value: unknown): string {
  if (value == null) return "";
  if (typeof value === "string") {
    return (
      MESSAGE_KEY_TEXT[value] ||
      ERROR_CODE_MESSAGES[value] ||
      PLAIN_ERROR_MESSAGES[value] ||
      sanitizePlainError(value) ||
      value
    );
  }
  if (value instanceof Error) return value.message;

  const errorText = formatBackendError(value);
  if (errorText) return errorText;

  return "操作没有完成，请稍后重试";
}

const ERROR_CODE_MESSAGES: Record<string, string> = {
  ACADEMIC_TERM_NOT_FOUND: "没有找到这个学期",
  ANNOUNCEMENT_INVALID_TIME_RANGE: "公告结束时间不能早于开始时间",
  ANNOUNCEMENT_NOT_FOUND: "没有找到这条公告",
  INCORRECT_USER_PASSWD: "用户名或密码不正确",
  AUTH_TOKEN_INVALID: "登录状态已失效，请重新登录",
  CLUB_ACTIVITY_CREATE_REQUEST_MODERATED: "这条活动创建申请已经审核过",
  CLUB_ACTIVITY_CREATE_REQUEST_NOT_FOUND: "没有找到这条活动创建申请",
  CLUB_ACTIVITY_INVALID_TIME_RANGE: "活动结束时间必须晚于开始时间",
  CLUB_ACTIVITY_NOT_FOUND: "没有找到这个社团活动",
  CLUB_ACTIVITY_UPDATE_REQUEST_MODERATED: "这条活动修改申请已经审核过",
  CLUB_ACTIVITY_UPDATE_REQUEST_NOT_FOUND: "没有找到这条活动修改申请",
  CLUB_ACTIVITY_WRONG_BELONG: "该活动不属于当前社团",
  CLUB_GENERAL_ACTIVITY_RECORD_NOT_FOUND: "没有找到这条社团综评记录",
  CLUB_NOT_ACTIVE: "该社团当前不可操作",
  CLUB_NOT_FOUND: "没有找到这个社团",
  CLUB_ROLE_NOT_ALLOWED: "你不是该社团的负责人，无法执行此操作",
  CLUB_UPDATE_REQUEST_MODERATED: "这条社团资料修改申请已经审核过",
  CLUB_UPDATE_REQUEST_NOT_FOUND: "没有找到这条社团资料修改申请",
  DATABASE_CONFLICT: "数据已被更新，请刷新后重试",
  DATABASE_UNAVAILABLE: "数据库暂时不可用，请稍后重试",
  DUPLICATE_CLUB_NAME: "社团名称已被使用",
  DUPLICATE_CLUB_REQUESTED: "该社团已经提交过这个大型活动申请",
  DUPLICATE_EMAIL: "邮箱已被使用",
  DUPLICATE_JOIN_REQUEST: "你已经提交过加入申请或已经是该社团成员",
  DUPLICATE_PENDING_REQUEST: "已经有待审核的申请，请等待处理后再提交",
  DUPLICATE_STAR_LEVEL_APPLICATION: "本学期已经提交过星级评价申请",
  DUPLICATE_USERNAME: "用户名已被使用",
  GENERAL_ACTIVITY_INVALID_TIME_RANGE: "大型活动结束时间不能早于开始时间",
  GENERAL_ACTIVITY_NOT_FOUND: "没有找到这个大型活动",
  INVALID_MODERATION_STATUS: "审核结果只能选择通过或驳回",
  IS_NOT_MEMBER: "你当前不是该社团成员",
  NON_NULLABLE_FIELD_NULL: "必填字段不能留空",
  NOT_ALLOWED_LEAVE_CLUB: "社长或副社长不能直接退出社团，请先移交职位",
  RECORD_NOT_FOUND: "没有找到这条申请记录",
  RECORD_REVIEWED: "这条活动记录已经审核过，不能再次修改",
  RESOURCE_NOT_FOUND: "请求的内容不存在",
  ROLE_NOT_ALLOWED: "你没有执行此操作的权限",
  STAR_LEVEL_NOT_FOUND: "没有找到这条星级评价申请",
  STAR_LEVEL_UPDATE_DENIED: "已通过的星级评价申请不能再修改",
  UPDATE_REQUEST_IS_NULL: "请至少填写一项需要修改的内容",
  USER_BANNED: "该账号已被封禁，无法执行此操作",
  USER_NOT_FOUND: "没有找到这个用户",
  USER_UPDATE_REQUEST_MODERATED: "这条用户资料修改申请已经审核过",
  USER_UPDATE_REQUEST_NOT_FOUND: "没有找到这条用户资料修改申请",
};

const MESSAGE_KEY_TEXT: Record<string, string> = {
  "error.academic_term.not_found": "没有找到这个学期",
  "error.announcement.invalid_time_range": "公告结束时间不能早于开始时间",
  "error.announcement.not_found": "没有找到这条公告",
  "error.auth.incorrect_user_passwd": "用户名或密码不正确",
  "error.auth.token_invalid": "登录状态已失效，请重新登录",
  "error.club.duplicate_join_request": "你已经提交过加入申请或已经是该社团成员",
  "error.club.duplicate_club_name": "社团名称已被使用",
  "error.club.is_not_member": "你当前不是该社团成员",
  "error.club.not_active": "该社团当前不可操作",
  "error.club.not_allowed_leave": "社长或副社长不能直接退出社团，请先移交职位",
  "error.club.not_found": "没有找到这个社团",
  "error.club.role_not_allowed": "你不是该社团的负责人，无法执行此操作",
  "error.club.update_request_not_found": "没有找到这条社团资料修改申请",
  "error.club_activity_create_request.moderated": "这条活动创建申请已经审核过",
  "error.club_activity_create_request.not_found": "没有找到这条活动创建申请",
  "error.club_activity.invalid_time_range": "活动结束时间必须晚于开始时间",
  "error.club_activity.not_found": "没有找到这个社团活动",
  "error.club_activity_update_request.moderated": "这条活动修改申请已经审核过",
  "error.club_activity_update_request.not_found": "没有找到这条活动修改申请",
  "error.club_activity.wrong_belong": "该活动不属于当前社团",
  "error.club_general_activity_record.not_found": "没有找到这条社团综评记录",
  "error.club_update_request.moderated": "这条社团资料修改申请已经审核过",
  "error.club_update_request.not_found": "没有找到这条社团资料修改申请",
  "error.database.conflict": "数据已被更新，请刷新后重试",
  "error.database.unavailable": "数据库暂时不可用，请稍后重试",
  "error.general_activity.club_requested": "该社团已经提交过这个大型活动申请",
  "error.general_activity.invalid_time_range":
    "大型活动结束时间不能早于开始时间",
  "error.general_activity.not_found": "没有找到这个大型活动",
  "error.general_activity.record_not_found": "没有找到这条申请记录",
  "error.general_activity.record_reviewed":
    "这条活动记录已经审核过，不能再次修改",
  "error.moderation.duplicate_pending_request":
    "已经有待审核的申请，请等待处理后再提交",
  "error.request_moderate.invalid_moderation_status":
    "审核结果只能选择通过或驳回",
  "error.role.not_allowed": "你没有执行此操作的权限",
  "error.star_level.denied": "已通过的星级评价申请不能再修改",
  "error.star_level.duplicate_application": "本学期已经提交过星级评价申请",
  "error.star_level.not_found": "没有找到这条星级评价申请",
  "error.update_request.is_null": "请至少填写一项需要修改的内容",
  "error.update_request.non_nullable_field_null": "必填字段不能留空",
  "error.user.banned": "该账号已被封禁，无法执行此操作",
  "error.user.duplicate_email": "邮箱已被使用",
  "error.user.duplicate_username": "用户名已被使用",
  "error.user.not_found": "没有找到这个用户",
  "error.user_update_request.moderated": "这条用户资料修改申请已经审核过",
  "error.user_update_request.not_found": "没有找到这条用户资料修改申请",
};

const PLAIN_ERROR_MESSAGES: Record<string, string> = {
  "File too large": "文件太大，请选择更小的文件",
  "Incorrect username or password": "用户名或密码不正确",
  "Invalid authentication credentials": "请先登录或重新登录",
  "Not authenticated": "请先登录",
  "Unsupported content type": "不支持这个文件类型",
  "Unsupported file extension": "不支持这个文件后缀",
};

function formatBackendError(value: unknown): string {
  if (!value || typeof value !== "object") return "";
  const record = value as Record<string, unknown>;
  const payload =
    record.response && typeof record.response === "object"
      ? ((record.response as Record<string, unknown>).data as Record<
          string,
          unknown
        >) || record
      : record;

  const code = payload.error_code || payload.code;
  if (typeof code === "string" && ERROR_CODE_MESSAGES[code]) {
    return `${ERROR_CODE_MESSAGES[code]}${formatDetails(payload.details)}`;
  }

  const messageKey = payload.message_key;
  if (typeof messageKey === "string" && MESSAGE_KEY_TEXT[messageKey]) {
    return `${MESSAGE_KEY_TEXT[messageKey]}${formatDetails(payload.details)}`;
  }

  const detail = payload.detail || payload.message;
  if (Array.isArray(detail)) {
    return formatValidationErrors(detail);
  }
  if (typeof detail === "string") {
    return (
      MESSAGE_KEY_TEXT[detail] ||
      ERROR_CODE_MESSAGES[detail] ||
      PLAIN_ERROR_MESSAGES[detail] ||
      sanitizePlainError(detail) ||
      detail
    );
  }
  if (detail && typeof detail === "object") {
    return formatBackendError(detail);
  }

  const status = Number(payload.status || (record.response as any)?.status);
  if (status === 401) return "登录状态已失效，请重新登录";
  if (status === 403) return "你没有执行此操作的权限";
  if (status === 404) return "请求的内容不存在";
  if (status >= 500) return "服务器暂时不可用，请稍后重试";

  return "";
}

function formatValidationErrors(items: unknown[]): string {
  const messages = items
    .map((item) => {
      if (!item || typeof item !== "object") return "";
      const record = item as Record<string, unknown>;
      const fieldKey = Array.isArray(record.loc)
        ? record.loc
            .filter((part) => !["body", "query", "path"].includes(String(part)))
            .join(".")
        : "";
      const field = FIELD_LABELS[fieldKey] || fieldKey || "字段";
      const message = formatValidationMessage(record);
      return `${field || "字段"}：${message}`;
    })
    .filter(Boolean);
  return messages.join("；") || "提交内容格式不正确";
}

function formatDetails(details: unknown): string {
  if (!details || typeof details !== "object" || Array.isArray(details)) {
    return "";
  }
  const labelMap: Record<string, string> = {
    academic_term_id: "学期 ID",
    activity_id: "活动 ID",
    announcement_id: "公告 ID",
    club_activity_id: "社团活动 ID",
    club_id: "社团 ID",
    email: "邮箱",
    field: "字段",
    general_activity_id: "大型活动 ID",
    record_id: "记录 ID",
    request_id: "申请 ID",
    star_level_id: "星级评价申请 ID",
    term_id: "学期 ID",
    user_id: "用户 ID",
    username: "用户名",
  };
  const parts = Object.entries(details as Record<string, unknown>)
    .filter(([, detailValue]) => detailValue != null && detailValue !== "")
    .map(
      ([key, detailValue]) => `${labelMap[key] || key}: ${String(detailValue)}`,
    );
  return parts.length ? `（${parts.join("，")}）` : "";
}

const FIELD_LABELS: Record<string, string> = {
  activity_id: "活动",
  article_url: "文章链接",
  audit_status: "审核状态",
  avatar_uri: "头像",
  body: "正文",
  category: "社团类别",
  club_id: "社团",
  content_type: "文件类型",
  description: "描述",
  email: "邮箱",
  end_date: "结束日期",
  ends_at: "结束展示时间",
  end_time: "结束时间",
  filename: "文件名",
  final_score: "最终分数",
  grade: "年级",
  growth_story_url: "成长故事链接",
  is_active: "启用状态",
  level: "活动级别",
  link_url: "链接",
  location: "地点",
  logo_uri: "社团标志",
  name: "名称",
  participation_type: "参与类型",
  password: "密码",
  poster_uri: "海报",
  proof_files: "证明材料",
  requested_contest_score: "申请竞赛分",
  requested_score: "申请分数",
  scene: "上传场景",
  size: "文件大小",
  star_level: "星级",
  start_date: "开始日期",
  starts_at: "开始展示时间",
  start_time: "开始时间",
  status: "状态",
  summary: "简介",
  target_grade_1: "目标级部 1",
  target_grade_2: "目标级部 2",
  term_name: "学期名称",
  title: "标题",
  uniqueness_statement: "特色说明",
  update_fields: "修改字段",
  username: "用户名",
};

function formatValidationMessage(record: Record<string, unknown>): string {
  const msg = typeof record.msg === "string" ? record.msg : "";
  const ctx =
    record.ctx && typeof record.ctx === "object"
      ? (record.ctx as Record<string, unknown>)
      : {};

  if (msg === "Field required") return "不能为空";
  if (msg.includes("valid integer")) return "应为整数";
  if (msg.includes("valid number")) return "应为数字";
  if (msg.includes("valid boolean")) return "应为是或否";
  if (msg.includes("valid string")) return "应为文本";
  if (msg.includes("valid URL")) return "应为有效链接";
  if (msg.includes("valid email")) return "应为有效邮箱";
  if (msg.includes("valid datetime")) return "应为有效日期时间";
  if (msg.includes("valid date")) return "应为有效日期";
  if (msg.includes("greater than")) return "数值过小";
  if (msg.includes("less than")) return "数值过大";
  if (msg.includes("String should have at most")) {
    return typeof ctx.max_length === "number"
      ? `不能超过 ${ctx.max_length} 个字符`
      : "长度过长";
  }
  if (msg.includes("String should have at least")) {
    return typeof ctx.min_length === "number"
      ? `至少需要 ${ctx.min_length} 个字符`
      : "长度过短";
  }
  if (msg.includes("Input should be")) return "取值不在允许范围内";

  return msg || "格式不正确";
}

function sanitizePlainError(value: string): string {
  const trimmed = value.trim();
  if (!trimmed) return "";
  if (
    trimmed.startsWith("<!doctype") ||
    trimmed.startsWith("<html") ||
    trimmed.includes("<body")
  ) {
    return "后端接口没有返回可识别的错误信息，请确认服务地址和路由配置正确";
  }
  return "";
}

export function formatDate(value?: string | null): string {
  if (!value) return "未设置";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleDateString();
}

export function formatDateTime(value?: string | null): string {
  if (!value) return "未设置";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString();
}

export function toDateTimeLocalValue(value?: string | null): string {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  const offsetDate = new Date(
    date.getTime() - date.getTimezoneOffset() * 60000,
  );
  return offsetDate.toISOString().slice(0, 16);
}

export function fromDateTimeLocalValue(value: string): string {
  return new Date(value).toISOString();
}

export function toNumberOrZero(value: string): number {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : 0;
}

export function nullableNumber(value: string): number | null {
  const trimmed = value.trim();
  if (!trimmed) return null;
  const parsed = Number(trimmed);
  return Number.isFinite(parsed) ? parsed : null;
}

export function nullableText(value: string): string | null {
  const trimmed = value.trim();
  return trimmed ? trimmed : null;
}

export function splitLines(value: string): string[] | null {
  const items = value
    .split(/\r?\n/)
    .map((item) => item.trim())
    .filter(Boolean);
  return items.length ? items : null;
}
