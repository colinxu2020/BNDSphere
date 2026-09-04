# BNDSphere 后端 API 参考

> 本文档只描述**路由拓扑、鉴权要求和行为**；请求体/响应体的精确字段以运行中的服务自动生成的 OpenAPI 文档为准（`/api/docs`、`/api/redoc`、`/api/openapi.json`），前端的 `frontend/src/api/schema.d.ts` 就是从它生成的。手工誊抄字段级 schema 很容易和代码漂移，本文档刻意不重复那部分。
>
> 所有路由都挂在 `/api/v1` 前缀下（见 `app/main.py`、`app/api/v1/__init__.py`）；下表中的路径均为相对于 `/api/v1` 的路径。

## 通用约定

- **鉴权**：`Authorization: Bearer <JWT>`，通过 `POST /auth/login` 获取（OAuth2 password flow，`tokenUrl=/api/v1/auth/login`）。下表"鉴权"列里：
  - **公开**：无需登录。
  - **登录**：需要有效 token，但无角色/职务限制（对应 `Depends(get_current_user)`）。
  - **全局角色：`X`**：需要 `RoleEnum` 属于 `X`（`RoleChecker`）；`dev` 角色对所有此类检查免检（见 [overview.md](overview.md)）。
  - **社团职务：`X`**：需要当前用户在路径里的 `{club_id}` 对应社团里的 `ClubMembershipEnum` 属于 `X`（`ClubRoleChecker`）；`admin`/`dev` 免检。
  - 处于 `role=ban` 的用户在任何需要登录的接口上都会被拒绝（`AccessPolicy.ensure_user_active`）。
- **错误响应**：业务错误统一返回 `{"message_key": str, "error_code": str, "details": dict}`，状态码由异常类型决定（401/400/403/404/409，见 `services/errors.py`）。
- **分页**：列表接口统一返回 `fastapi_pagination` 的 `Page[...]`（`items`/`total`/`page`/`size`/`pages`），查询参数 `page`/`size` 由 `fastapi-pagination` 自动注入。
- **搜索**：带 `search` 参数的接口是对相关文本字段的模糊匹配（`clubs` 用 `pg_trgm` GIN 索引，其它表多为 `ILIKE`）。

---

## Auth — `/auth`（公开）

| 方法 | 路径        | 鉴权 | 说明                                                                 |
| ---- | ----------- | ---- | ---------------------------------------------------------------------- |
| POST | `/register` | 公开 | 注册新用户，`username` 全局唯一（`409` 冲突）。                        |
| POST | `/login`    | 公开 | OAuth2 password flow（表单字段 `username`/`password`，其余表单字段忽略），返回 JWT。密码错误 `401`。 |

## Users — `/users`

| 方法 | 路径               | 鉴权 | 说明                                                                              |
| ---- | ------------------ | ---- | --------------------------------------------------------------------------------- |
| GET  | `/me`               | 登录 | 当前用户的完整资料。                                                              |
| GET  | `/{user_id}`        | 公开 | 指定用户的公开资料（不含角色等敏感字段）。`404` 未找到。                          |
| POST | `/update-requests`  | 登录 | 提交个人资料修改申请（moderation）。同一用户至多一条 pending 申请，新申请会顶掉旧的 pending 申请（不是报错）。 |

管理员/审核员对用户的操作分别在 [Admin](#admin--admin) 和 [Moderations](#moderations--moderations) 里。

## Clubs — `/clubs`

| 方法   | 路径                                | 鉴权                     | 说明                                                                                          |
| ------ | ----------------------------------- | ------------------------ | ------------------------------------------------------------------------------------------------ |
| GET    | `/`                                  | 公开                      | 分页搜索社团，仅返回 `status=normal`；`search`、`category` 可选过滤。                             |
| GET    | `/{club_id}`                         | 公开                      | 获取单个社团信息；仅 `status=normal` 的社团可获取，否则 `403 CLUB_NOT_ACTIVE`。                    |
| POST   | `/`                                  | 登录                      | 创建新社团，创建者自动成为 `president`。社团名在未归档社团中必须唯一，冲突 `409`。                 |
| POST   | `/{club_id}/update-requests`         | 社团职务：`president`/`vice_president` | 提交社团资料修改申请（moderation）。同一社团至多一条 pending 申请，新申请顶掉旧的。          |
| POST   | `/{club_id}/membership-requests`     | 登录                      | 申请加入社团（verification）。已是有效成员（非 `left`）时 `409` 重复申请。                        |
| DELETE | `/{club_id}/members/me`              | 登录                      | 退出社团。社长/副社长不能直接退出（`403`），需先转让职务/被移除职务。非成员 `404`。                |
| PATCH  | `/{club_id}/members/{user_id}`       | 社团职务：`president`     | 任命/罢免副社长，或转让社长职位给目标成员（此时操作者自己降为普通成员）。                          |
| DELETE | `/{club_id}/members/{user_id}`       | 社团职务：`president`     | 移出成员（置为 `left`）。不能移除社长自己。                                                       |

## Club Activities — `/clubs/{club_id}/activities`

社团活动本身没有直接的写接口——创建/修改都要走审核（见下方 Moderations）。

| 方法 | 路径                              | 鉴权                                          | 说明                                             |
| ---- | ---------------------------------- | ----------------------------------------------- | ------------------------------------------------- |
| GET  | `/`                                  | 公开                                              | 列出该社团的全部活动。                             |
| POST | `/create-requests`                   | 社团职务：`president`/`vice_president`            | 提交"新建活动"申请（moderation）。                 |
| POST | `/update-requests/{activity_id}`     | 社团职务：`president`/`vice_president`            | 提交"修改活动"申请（moderation）；同一活动至多一条 pending 申请，新申请顶掉旧的；时间范围必须完整且合法。 |

## Club General Activities — `/clubs/{club_id}/general-activities`

社团参与校级/大型活动的记录，走 `AuditMixin`（简单审核流，非独立申请表）。

| 方法  | 路径 | 鉴权                                | 说明                                                                          |
| ----- | ---- | ------------------------------------- | ------------------------------------------------------------------------------- |
| GET   | `/`   | 公开                                    | 列出该社团参加过的所有通用活动记录。                                            |
| POST  | `/`   | 社团职务：`president`/`vice_president`  | 创建一条参与记录（申请分数、证明材料）；同一社团对同一活动只能创建一条，重复 `409`。 |
| PATCH | `/`   | 社团职务：`president`/`vice_president`  | 修改一条**尚未审核**的记录（`audit_status != pending` 时 `403`）。               |

## Club Star Level — `/clubs/{club_id}/star-level`

| 方法 | 路径 | 鉴权                     | 说明                                                                    |
| ---- | ---- | -------------------------- | -------------------------------------------------------------------------- |
| GET  | `/`   | 社团职务：`president`      | 列出该社团历次星级评定申请。                                              |
| POST | `/`   | 社团职务：`president`      | 提交本学期的星级评定申请。同一社团同一学期只能有一条申请（`uq_star_level_applications_club_id_academic_term_id`），重复 `409`。 |

## Club Star Rating — `/clubs/{club_id}/star-rating`

| 方法 | 路径 | 鉴权 | 说明                                                                                     |
| ---- | ---- | ---- | ------------------------------------------------------------------------------------------ |
| GET  | `/`   | 公开  | 实时计算并返回该社团当前学期的星级评分明细（不落库）。评分规则见 [../business_process.md](../business_process.md)。 |

## Club Joint Activities — `/clubs/{club_id}/joint-activities`

社团管理侧（社长/副社长）对联合活动的全生命周期操作，鉴权统一为**社团职务：`president`/`vice_president`**。

| 方法  | 路径                            | 说明                                                                                     |
| ----- | -------------------------------- | -------------------------------------------------------------------------------------------- |
| GET   | `/`                                | 列出该社团相关的联合活动（发起的 + 参与的），含未公开的。                                    |
| POST  | `/`                                | 发起一个联合活动（初审状态 `pending`）。                                                     |
| PATCH | `/{activity_id}`                  | 修改活动信息（仅发起社团可改）；初审已通过（`preliminary_status=approved`）后不可再改，`403`；改后初审状态会被重置为 `pending`，需要重新初审。 |
| POST  | `/{activity_id}/participations`   | 为本社团报名参加该活动。要求初审已通过、活动尚未结束、本社团未重复报名。                     |
| PATCH | `/{activity_id}/archive`          | 更新结项文字/材料（仅发起社团）。要求初审已通过、活动已结束、终审未处于 `pending`/`approved` 锁定态。 |
| POST  | `/{activity_id}/final-submission` | 提交终审（结项审核），把 `final_status` 置为 `pending`。要求已填写结项文字或材料，否则 `400`。 |

## Star Level — `/star-level`（跨社团只读 + 申请人自助修改）

| 方法  | 路径              | 鉴权                                | 说明                                                                              |
| ----- | ------------------ | ------------------------------------- | ------------------------------------------------------------------------------------ |
| GET   | `/`                  | 公开                                    | 按创建时间倒序列出全部星级评定申请（跨社团）。                                       |
| GET   | `/{star_level_id}`   | 公开                                    | 获取单条申请详情。`404` 未找到。                                                     |
| PATCH | `/{star_level_id}`   | 社团职务：`president`（该申请所属社团） | 申请人（社长）自行修改**尚未审核通过**的申请内容；已 `approved` 的申请不可再改（`403`）。 |

星级评定的**审核**（决定通过/驳回、给分）在社联侧接口里，见下方 [Club Federation → Star Level](#star-level-1)。

## General Activities — `/general-activities`（公开只读）

| 方法 | 路径             | 鉴权 | 说明                                                                     |
| ---- | ----------------- | ---- | --------------------------------------------------------------------------- |
| GET  | `/{activity_id}`   | 公开  | 获取单个通用活动。`404` 未找到。                                            |
| GET  | `/`                 | 公开  | 分页列出通用活动；`search`、`level`、`starts_before`、`ends_after`、`has_poster` 可选过滤。 |

通用活动的创建/修改/删除在社联侧（[Club Federation → General Activities](#general-activities-1)）和管理员侧（[Admin → General Activities](#general-activities-2)）。

## Joint Activities — `/joint-activities`（公开只读，仅展示已公开的）

| 方法 | 路径             | 鉴权 | 说明                                                        |
| ---- | ----------------- | ---- | -------------------------------------------------------------- |
| GET  | `/`                 | 公开  | 列出初审已通过（`preliminary_status=approved`）的联合活动。`search` 可选。 |
| GET  | `/{activity_id}`    | 公开  | 获取单个已公开的联合活动；未公开或不存在均 `404`。               |

## Announcements — `/announcements`（公开只读）

| 方法 | 路径 | 鉴权 | 说明                                                                                       |
| ---- | ---- | ---- | ---------------------------------------------------------------------------------------------- |
| GET  | `/`   | 公开  | 分页列出公告；`active_only`（默认 `true`）时只返回 `is_active=True` 且当前时间落在生效窗口内的公告；`search` 可选。 |

管理端见 [Admin → Announcements](#announcements-1)。

## Uploads — `/uploads`（登录用户直传 OSS）

| 方法 | 路径         | 鉴权 | 说明                                                                                          |
| ---- | ------------- | ---- | ------------------------------------------------------------------------------------------------ |
| POST | `/initiate`   | 登录  | 按 `scene`（`avatar`/`club_logo`/`activity_poster`/`application_file`/`joint_activity_archive`）校验声明的文件大小/类型/扩展名，返回一个有时效的 OSS PUT 预签名 URL。 |
| POST | `/confirm`    | 登录  | 前端直传 OSS 完成后调用；后端用 OSS HEAD 请求核实对象真实存在且大小未超限，返回可公开访问的 URL。 |

详见 [overview.md → 文件上传流程](overview.md#文件上传流程)。

---

## Moderations — `/moderations`

统一要求**全局角色：`moderator`/`admin`/`dev`**。审核通过时把请求表中的字段写回目标记录（社团/社团活动/用户资料），驳回或撤销均不影响目标记录。

### Users — `/moderations/users`

| 方法  | 路径                        | 说明                                    |
| ----- | ---------------------------- | ------------------------------------------ |
| GET   | `/update-requests`            | 列出全部待审核的用户资料修改申请。          |
| PATCH | `/update-requests/{request_id}` | 审核（通过/驳回）一条用户资料修改申请。     |

### Club Activities — `/moderations/club-activities`

| 方法  | 路径                                | 说明                                        |
| ----- | ------------------------------------- | ----------------------------------------------- |
| GET   | `/create-requests`                     | 列出待审核的"新建社团活动"申请。                |
| PATCH | `/create-requests/{request_id}`        | 审核"新建社团活动"申请；通过则在 `club_activities` 建一行新活动。 |
| GET   | `/update-requests`                     | 列出待审核的"修改社团活动"申请。                |
| PATCH | `/update-requests/{request_id}`        | 审核"修改社团活动"申请；通过则局部更新目标活动。 |

### Clubs — `/moderations/clubs`

| 方法  | 路径                          | 说明                                        |
| ----- | ------------------------------- | ----------------------------------------------- |
| GET   | `/update-requests`               | 列出待审核的社团资料修改申请。                  |
| PATCH | `/update-requests/{request_id}`  | 审核社团资料修改申请；通过则局部更新目标社团。   |

## Verifications — `/clubs/{club_id}/membership-requests`

统一要求**社团职务：`president`/`vice_president`**（对应该 `{club_id}`）。

| 方法  | 路径             | 说明                                                                    |
| ----- | ------------------ | ---------------------------------------------------------------------------- |
| GET   | ``                  | 列出该社团待处理的加入申请。                                                |
| PATCH | `/{request_id}`     | 核验（通过/驳回）一条加入申请；通过则把申请人写入 `club_members`（`member`）。 |

## Club Federation — `/club-federation`

统一要求**全局角色：`federation_staff`/`admin`/`dev`**（社联工作人员视角）。

### General Activities — `/club-federation/general-activity`

| 方法   | 路径              | 说明                       |
| ------ | ------------------- | ------------------------------ |
| POST   | `/`                   | 创建一个通用活动（校级/大型/社联活动）。 |
| PATCH  | `/{activity_id}`      | 修改通用活动。`404` 未找到。   |
| DELETE | `/{activity_id}`      | 删除通用活动。`404` 未找到。   |

### General Activity Club Records — `/club-federation/general-activity/club-records`

| 方法  | 路径             | 说明                                                              |
| ----- | ------------------ | ---------------------------------------------------------------------- |
| PATCH | `/{record_id}`      | 审核一条社团通用活动记录（给 `final_score`、设置 `audit_status`）。`404` 未找到。 |

### Star Level — `/club-federation/star-level`

| 方法  | 路径                        | 说明                                                                                 |
| ----- | ----------------------------- | ------------------------------------------------------------------------------------------ |
| POST  | `/{star_level_id}/preview`     | **不落库**，预览"如果按这个审核结果通过，会得多少分/几星"（用于社联审核时先看效果）。       |
| PATCH | `/{star_level_id}`             | 正式审核星级评定申请；通过时重新计算总分/星级并写回申请与 `clubs.star_level`。               |

### Joint Activities — `/club-federation/joint-activities`

| 方法  | 路径                                 | 说明                                                                 |
| ----- | -------------------------------------- | ------------------------------------------------------------------------- |
| GET   | `/`                                      | 列出全部联合活动（不限公开状态），`search` 可选，社联审核视角。          |
| PATCH | `/{activity_id}/preliminary-review`      | 初审（决定是否公开可报名）。仅能对 `preliminary_status=pending` 的活动操作。 |
| PATCH | `/{activity_id}/final-review`            | 终审（结项打分，`final_score` 需在 `6~8` 分之间，通过时不能低于 6）。仅能对 `final_status=pending` 的活动操作。 |

---

## Admin — `/admin`

统一要求**全局角色：`admin`/`dev`**。

### Users — `/admin/users`

| 方法  | 路径         | 说明                                                       |
| ----- | -------------- | -------------------------------------------------------------- |
| GET   | `/`             | 分页列出用户；`search`、`role` 可选过滤。                       |
| PATCH | `/{user_id}`    | 直接修改用户信息（含 `role`、`email` 等，不经过审核流程）。`404` 未找到。 |

### Clubs — `/admin/clubs`

| 方法  | 路径         | 说明                                                                 |
| ----- | -------------- | -------------------------------------------------------------------------- |
| GET   | `/`             | 分页列出社团（不限 `status`）；`search`、`category`、`club_status` 可选。   |
| GET   | `/{club_id}`    | 获取任意状态的社团信息（不像公开接口那样限定 `status=normal`）。`404` 未找到。 |
| PATCH | `/{club_id}`    | 直接修改社团信息，含 `status`（审核创建申请 / 归档）、`star_level`，不经过审核流程。`404` 未找到。 |

### Academic Terms — `/admin/academic-terms`

| 方法   | 路径                    | 说明                                             |
| ------ | ------------------------- | ---------------------------------------------------- |
| GET    | `/`                         | 按开始日期倒序列出全部学期。                          |
| POST   | `/`                         | 创建学期；若 `is_current=true`，先清空其它学期的当前标记。 |
| GET    | `/{term_id}`                | 获取单个学期。`404` 未找到。                          |
| PATCH  | `/{term_id}`                | 修改学期。`404` 未找到。                              |
| DELETE | `/{term_id}`                | 删除学期。`404` 未找到。                              |
| POST   | `/{term_id}/set-current`    | 将该学期设为"当前学期"（先清空其它学期）。`404` 未找到。 |

### General Activities — `/admin/general-activities`

| 方法   | 路径             | 说明                                     |
| ------ | ------------------ | -------------------------------------------- |
| GET    | `/`                  | 分页列出通用活动；`search`、`level` 可选。   |
| POST   | `/`                  | 创建通用活动（与社联侧同一动作，管理员也可执行）。 |
| PATCH  | `/{activity_id}`     | 修改通用活动。`404` 未找到。                  |
| DELETE | `/{activity_id}`     | 删除通用活动。`404` 未找到。                  |

### Announcements — `/admin/announcements`

| 方法   | 路径                  | 说明                                                          |
| ------ | ----------------------- | ------------------------------------------------------------------ |
| GET    | `/`                       | 分页列出公告（默认包含未生效/已过期的，`active_only` 默认 `false`）。 |
| POST   | `/`                       | 创建公告。                                                          |
| PATCH  | `/{announcement_id}`      | 修改公告。`404` 未找到。                                             |
| DELETE | `/{announcement_id}`      | 删除公告。`404` 未找到。                                             |

---

## 其它

- `GET /health`（不在 `/api/v1` 前缀下，路径就是 `/health`）：无鉴权的存活检查，`204 No Content`，供 Docker healthcheck 使用。
