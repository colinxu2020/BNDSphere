# BNDSphere 后端 API 参考

> 目标：给出每个接口的**请求 / 响应 schema、权限要求、可能的错误码**——但只报出 Pydantic schema 的**类名**（源码在 `backend/app/schemas/`），不誊抄字段级细节。字段本身以运行中服务自动生成的 OpenAPI 文档为准（`/api/docs` Swagger UI、`/api/redoc`、`/api/openapi.json`）；前端的 `frontend/src/api/schema.d.ts` 就是从它生成的。手工誊抄字段很容易和代码漂移，这也是旧版文档出错的原因之一，本文档刻意不重复那部分。
>
> 所有路由都挂在 `/api/v1` 前缀下（`app/main.py`、`app/api/v1/__init__.py`）；下面表格里的路径均为相对于 `/api/v1` 的路径。业务流程/时序见 [../business_process.md](../business_process.md)；分层与访问控制机制见 [overview.md](overview.md)。

## 约定

- **鉴权**：`Authorization: Bearer <JWT>`，由 `POST /auth/login` 签发。**权限**列的取值：
  - `公开` — 无需登录。
  - `登录` — 需要有效 token（`Depends(get_current_user)`），无额外角色限制。
  - `角色:X` — 全局角色需属于 `X`（`RoleChecker`，见 `app/models/user.py::RoleEnum`）；`dev` 对所有此类检查免检。
  - `职务:X`(club) — 当前用户在路径 `{club_id}` 对应社团里的职务（`ClubMembershipEnum`）需属于 `X`（`ClubRoleChecker`）；`admin`/`dev` 免检。
  - `role=ban` 的用户在任何需要登录的接口上都会被 `USER_BANNED` 拒绝（`AccessPolicy.ensure_user_active`），下表不再逐条列出。
- **请求 / 响应**：`–` 表示无请求体或无响应体（`204`）。列表接口的响应统一是 `fastapi_pagination` 的 `Page[T]`（`items`/`total`/`page`/`size`/`pages`，`page`/`size` 查询参数自动注入），下表写作 `Page[T]`。
- **错误**：业务错误统一返回 `{"message_key": str, "error_code": str, "details": dict}`，状态码见 [错误码总表](#错误码总表)。**错误**列只列该接口路径上会主动抛出的业务错误码；未列出不代表不可能出现校验类错误（如必填字段缺失）——那些是 FastAPI/Pydantic 的标准 `422` 响应，形状不是上面这个 JSON 信封，不在本表范围内。
- **例外**：`POST /uploads/initiate` 的文件校验用的是原生 `fastapi.HTTPException`（`{"detail": str}`），不是上面的错误信封——是当前代码里唯一一处不遵循统一错误格式的接口，调用方需要单独处理。

## 错误码总表

按 HTTP 状态码分组；`error_code` 就是响应体 `error_code` 字段的值，源码见 `app/services/errors.py`（专用异常类）及各 `services`/`schemas` 模块（内联抛出的 `BusinessError` 子类）。

<details>
<summary><strong>401 Unauthorized</strong></summary>

| error_code             | 含义                         |
| ----------------------- | ---------------------------- |
| `AUTH_TOKEN_INVALID`     | token 缺失 / 无效 / 已过期    |
| `INCORRECT_USER_PASSWD`  | 用户名或密码错误（登录）       |

</details>

<details>
<summary><strong>400 Bad Request</strong></summary>

| error_code                          | 含义                                                          |
| ------------------------------------- | --------------------------------------------------------------- |
| `CLUB_ACTIVITY_INVALID_TIME_RANGE`     | 社团活动起止时间不合法（`end_time <= start_time`，或修改后不完整） |
| `GENERAL_ACTIVITY_INVALID_TIME_RANGE`  | 通用活动 `starts_at`/`ends_at` 不合法                            |
| `ANNOUNCEMENT_INVALID_TIME_RANGE`      | 公告 `starts_at`/`ends_at` 不合法                                |
| `JOINT_ACTIVITY_INVALID_TIME_RANGE`    | 联合活动起止时间不合法                                          |
| `JOINT_ACTIVITY_REGISTRATION_CLOSED`   | 活动已结束，不能再报名                                          |
| `JOINT_ACTIVITY_NOT_ENDED`             | 活动尚未结束，不能填写结项材料 / 提交终审                        |
| `JOINT_ACTIVITY_ARCHIVE_REQUIRED`      | 提交终审前必须先填写结项文字或材料                               |
| `JOINT_ACTIVITY_INVALID_FINAL_SCORE`   | 终审 `final_score` 超出 `[6, 8]`，或通过时低于 6 分                |
| `INVALID_MODERATION_STATUS`            | 审核结果只能是 `approved`/`rejected`                             |
| `INVALID_VERIFICATION_STATUS`          | 核验结果只能是 `approved`/`rejected`                             |
| `NON_NULLABLE_FIELD_NULL`              | 局部更新时显式把一个不可为空的字段传了 `null`                    |
| `UPDATE_REQUEST_IS_NULL`               | 审核类"修改申请"一个要改的字段都没提供                            |
| `UPLOAD_SCENE_MISMATCH`                | 确认上传时，object key 与声明的场景目录不匹配                    |
| `UPLOAD_OBJECT_TOO_LARGE`              | 确认上传时，OSS 记录的实际大小超过该场景上限                      |

</details>

<details>
<summary><strong>403 Forbidden</strong></summary>

| error_code                                | 含义                                                          |
| -------------------------------------------- | ----------------------------------------------------------------- |
| `USER_BANNED`                                 | 当前用户 `role=ban`                                              |
| `ROLE_NOT_ALLOWED`                            | 全局角色不满足接口要求                                            |
| `CLUB_ROLE_NOT_ALLOWED`                       | 社团职务不满足接口要求                                            |
| `CLUB_NOT_ACTIVE`                             | 目标社团 `status != normal`                                       |
| `CLUB_PRESIDENT_REQUIRED`                     | 需要是该社团社长（`ClubRoleChecker` 之外的内部兜底检查）            |
| `NOT_ALLOWED_LEAVE_CLUB`                      | 社长/副社长不能直接退出社团                                       |
| `CANNOT_CHANGE_PRESIDENT_ROLE`                | 不能把社长自己的职务改成"社长"以外的值（应走"转让社长"）             |
| `CANNOT_REMOVE_PRESIDENT`                     | 不能把社长移出社团                                                |
| `CLUB_UPDATE_REQUEST_MODERATED`               | 该社团资料修改申请已被审核过，不能重复审核                         |
| `CLUB_ACTIVITY_CREATE_REQUEST_MODERATED`      | 该"新建活动"申请已被审核过                                        |
| `CLUB_ACTIVITY_UPDATE_REQUEST_MODERATED`      | 该"修改活动"申请已被审核过                                        |
| `CLUB_ACTIVITY_WRONG_BELONG`                  | 目标活动不属于路径里的社团                                        |
| `CLUB_MEMBERSHIP_REQUEST_VERIFIED`            | 该加入申请已被核验过                                              |
| `RECORD_REVIEWED`                             | 该通用活动记录已审核，社团不能再自行修改                           |
| `USER_UPDATE_REQUEST_MODERATED`               | 该用户资料修改申请已被审核过                                       |
| `STAR_LEVEL_UPDATE_DENIED`                    | 该星级评定申请已通过，不能再改                                     |
| `JOINT_ACTIVITY_INITIATOR_REQUIRED`           | 只有发起社团能执行该操作                                          |
| `JOINT_ACTIVITY_PRELIMINARY_APPROVED`         | 初审已通过后不能再修改活动信息                                    |
| `JOINT_ACTIVITY_NOT_PUBLIC`                   | 初审尚未通过，活动还不能报名/结项                                  |
| `JOINT_ACTIVITY_FINAL_REVIEW_LOCKED`          | 终审已提交（pending/approved），结项材料被锁定不能再改              |
| `JOINT_ACTIVITY_PRELIMINARY_REVIEWED`         | 初审已经处理过，不能重复初审                                       |
| `JOINT_ACTIVITY_FINAL_REVIEW_NOT_PENDING`     | 终审不处于待审状态，不能执行终审操作                                |

</details>

<details>
<summary><strong>404 Not Found</strong></summary>

| error_code                              | 含义                    |
| ------------------------------------------ | ------------------------- |
| `USER_NOT_FOUND`                            | 用户不存在                |
| `CLUB_NOT_FOUND`                             | 社团不存在                |
| `CLUB_MEMBER_NOT_FOUND`                      | 目标不是该社团的有效成员    |
| `CLUB_ACTIVITY_NOT_FOUND`                    | 社团活动不存在             |
| `GENERAL_ACTIVITY_NOT_FOUND`                 | 通用活动不存在             |
| `ACADEMIC_TERM_NOT_FOUND`                    | 学期不存在                |
| `ANNOUNCEMENT_NOT_FOUND`                     | 公告不存在                |
| `STAR_LEVEL_NOT_FOUND`                       | 星级评定申请不存在          |
| `JOINT_ACTIVITY_NOT_FOUND`                   | 联合活动不存在             |
| `IS_NOT_MEMBER`                               | 当前用户不是该社团的有效成员（退出社团时） |
| `CLUB_UPDATE_REQUEST_NOT_FOUND`              | 社团资料修改申请不存在       |
| `CLUB_ACTIVITY_CREATE_REQUEST_NOT_FOUND`     | "新建活动"申请不存在        |
| `CLUB_ACTIVITY_UPDATE_REQUEST_NOT_FOUND`     | "修改活动"申请不存在        |
| `USER_UPDATE_REQUEST_NOT_FOUND`              | 用户资料修改申请不存在       |
| `CLUB_MEMBERSHIP_REQUEST_NOT_FOUND`          | 加入申请不存在              |
| `CLUB_GENERAL_ACTIVITY_RECORD_NOT_FOUND`     | 社团通用活动记录不存在（社联审核入口） |
| `RECORD_NOT_FOUND`                            | 同上，服务层内部兜底用的另一个 code（正常情况下 API 只会看到上面那个） |
| `UPLOAD_OBJECT_NOT_FOUND`                    | 确认上传时，OSS 上找不到该 object key |

> Swagger 文档里偶尔出现的 `RESOURCE_NOT_FOUND` 只是 `responses=` 里给 OpenAPI 用的**示例占位符**（`app/api/common_responses.py::RESOURCE_NOT_FOUND_RESPONSE`），实际运行时永远返回上面某个更具体的 code，不会真的返回字面量 `RESOURCE_NOT_FOUND`。

</details>

<details>
<summary><strong>409 Conflict</strong></summary>

| error_code                          | 含义                                                    |
| ------------------------------------- | ----------------------------------------------------------- |
| `DUPLICATE_USERNAME`                   | 用户名已被占用（注册）                                       |
| `DUPLICATE_EMAIL`                      | 邮箱已被占用                                                |
| `DUPLICATE_CLUB_NAME`                  | 社团名在未归档社团中已存在                                  |
| `DUPLICATE_JOIN_REQUEST`               | 已是该社团有效成员，不能重复申请加入                          |
| `DUPLICATE_PENDING_REQUEST`            | 并发提交导致的同类 pending 申请冲突（正常单请求下会被"顶替"逻辑吸收，见 [overview.md](overview.md)），罕见 |
| `DUPLICATE_STAR_LEVEL_APPLICATION`     | 该社团本学期已有星级评定申请                                |
| `DUPLICATE_CLUB_REQUESTED`             | 该社团已提交过同一通用活动的参与记录                          |
| `JOINT_ACTIVITY_CLUB_REGISTERED`       | 该社团已报名过该联合活动                                    |
| `DATABASE_CONFLICT`                    | 创建通用活动记录时的数据库层唯一约束冲突兜底                  |

</details>

<details>
<summary><strong>503 Service Unavailable</strong></summary>

| error_code             | 含义                     |
| ------------------------ | -------------------------- |
| `DATABASE_UNAVAILABLE`   | 创建通用活动记录时数据库不可达 |

</details>

---

## Auth — `/auth`

| 方法 | 路径        | 权限 | 请求               | 响应        | 错误                                   |
| ---- | ----------- | ---- | ------------------- | ----------- | ---------------------------------------- |
| POST | `/register` | 公开  | `UserCreate`         | `UserInfo`（201） | `DUPLICATE_USERNAME`                    |
| POST | `/login`    | 公开  | `OAuth2PasswordRequestForm`（表单 `username`/`password`，其余字段忽略） | `Token`     | `INCORRECT_USER_PASSWD`                 |

## Users — `/users`

| 方法 | 路径               | 权限 | 请求                     | 响应                    | 错误                          |
| ---- | ------------------ | ---- | -------------------------- | ------------------------- | ------------------------------ |
| GET  | `/me`               | 登录  | –                            | `UserInfo`                  | –                              |
| GET  | `/{user_id}`        | 公开  | –                            | `PublicUserInfo`             | `USER_NOT_FOUND`               |
| POST | `/update-requests`  | 登录  | `UserUpdateRequestCreate`    | `UserUpdateRequestInfo`（201） | `DUPLICATE_PENDING_REQUEST`    |

## Clubs — `/clubs`

| 方法   | 路径                            | 权限                      | 请求                                | 响应                          | 错误                                                                 |
| ------ | -------------------------------- | --------------------------- | -------------------------------------- | ------------------------------- | ------------------------------------------------------------------------ |
| GET    | `/`                                | 公开                          | Query: `search?`, `category?`            | `Page[ClubInfo]`                  | –                                                                         |
| GET    | `/{club_id}`                      | 公开                          | –                                         | `ClubInfo`                        | `CLUB_NOT_FOUND`, `CLUB_NOT_ACTIVE`                                        |
| POST   | `/`                                | 登录                          | `ClubCreate`                              | `ClubInfo`（201）                   | `DUPLICATE_CLUB_NAME`                                                     |
| POST   | `/{club_id}/update-requests`      | 职务: `president`/`vice_president` | `ClubUpdateRequestCreatePublic`           | `ClubUpdateRequestInfo`             | `CLUB_NOT_FOUND`, `CLUB_NOT_ACTIVE`, `DUPLICATE_PENDING_REQUEST`            |
| POST   | `/{club_id}/membership-requests`  | 登录                          | `ClubMembershipRequestCreatePublic`       | `ClubMembershipRequestInfo`（201）   | `CLUB_NOT_FOUND`, `CLUB_NOT_ACTIVE`, `DUPLICATE_JOIN_REQUEST`, `DUPLICATE_PENDING_REQUEST` |
| DELETE | `/{club_id}/members/me`           | 登录                          | –                                         | –（204）                           | `CLUB_NOT_FOUND`, `CLUB_NOT_ACTIVE`, `IS_NOT_MEMBER`, `NOT_ALLOWED_LEAVE_CLUB` |
| PATCH  | `/{club_id}/members/{user_id}`    | 职务: `president`             | `ClubMemberRoleUpdate`                    | `ClubMemberInfo`                    | `CLUB_NOT_FOUND`, `CLUB_NOT_ACTIVE`, `CLUB_MEMBER_NOT_FOUND`, `CANNOT_CHANGE_PRESIDENT_ROLE` |
| DELETE | `/{club_id}/members/{user_id}`    | 职务: `president`             | –                                         | –（204）                           | 同上 + `CANNOT_REMOVE_PRESIDENT`                                          |

## Club Activities — `/clubs/{club_id}/activities`

社团活动没有直接的增/改接口，均走审核（见 [Moderations](#moderations--moderations)）。

| 方法 | 路径                              | 权限                                | 请求                                    | 响应                              | 错误                                                                                              |
| ---- | ----------------------------------- | -------------------------------------- | ------------------------------------------ | ----------------------------------- | ----------------------------------------------------------------------------------------------------- |
| GET  | `/`                                    | 公开                                      | –                                             | `Page[ClubActivityInfo]`               | –                                                                                                       |
| POST | `/create-requests`                     | 职务: `president`/`vice_president`         | `ClubActivityCreateRequestCreatePublic`       | `ClubActivityCreateRequestInfo`（201）  | `CLUB_NOT_FOUND`, `CLUB_NOT_ACTIVE`                                                                    |
| POST | `/update-requests/{activity_id}`       | 职务: `president`/`vice_president`         | `ClubActivityUpdateRequestCreatePublic`       | `ClubActivityUpdateRequestInfo`         | `CLUB_NOT_FOUND`, `CLUB_NOT_ACTIVE`, `CLUB_ACTIVITY_NOT_FOUND`, `CLUB_ACTIVITY_WRONG_BELONG`, `CLUB_ACTIVITY_INVALID_TIME_RANGE`, `DUPLICATE_PENDING_REQUEST` |

## Club General Activities — `/clubs/{club_id}/general-activities`

| 方法  | 路径 | 权限                                | 请求                          | 响应                        | 错误                                                                                     |
| ----- | ---- | -------------------------------------- | -------------------------------- | ------------------------------ | -------------------------------------------------------------------------------------------- |
| GET   | `/`   | 公开                                      | –                                   | `Page[ClubGeneralActivityInfo]`   | `CLUB_NOT_FOUND`, `CLUB_NOT_ACTIVE`                                                          |
| POST  | `/`   | 职务: `president`/`vice_president`         | `ClubGeneralActivityCreate`         | `ClubGeneralActivityInfo`（201）    | `CLUB_NOT_FOUND`, `CLUB_NOT_ACTIVE`, `GENERAL_ACTIVITY_NOT_FOUND`, `DUPLICATE_CLUB_REQUESTED`, `DATABASE_CONFLICT`, `DATABASE_UNAVAILABLE` |
| PATCH | `/`   | 职务: `president`/`vice_president`         | `ClubGeneralActivityUpdate`         | `ClubGeneralActivityInfo`           | `CLUB_NOT_FOUND`, `CLUB_NOT_ACTIVE`, `GENERAL_ACTIVITY_NOT_FOUND`, `RECORD_REVIEWED`          |

## Club Star Level — `/clubs/{club_id}/star-level`

| 方法 | 路径 | 权限                | 请求                          | 响应                            | 错误                                          |
| ---- | ---- | ---------------------- | -------------------------------- | ---------------------------------- | ----------------------------------------------- |
| GET  | `/`   | 职务: `president`        | –                                   | `Page[StarLevelApplicationInfo]`     | `CLUB_NOT_FOUND`, `CLUB_NOT_ACTIVE`             |
| POST | `/`   | 职务: `president`        | `StarLevelApplicationCreate`        | `StarLevelApplicationInfo`（201）      | `DUPLICATE_STAR_LEVEL_APPLICATION`              |

## Club Star Rating — `/clubs/{club_id}/star-rating`

| 方法 | 路径 | 权限 | 请求 | 响应                  | 错误             |
| ---- | ---- | ---- | ---- | ----------------------- | ------------------ |
| GET  | `/`   | 公开  | –     | `StarRatingResponse`      | `CLUB_NOT_FOUND`   |

实时计算，不落库；评分算法见 [../business_process.md](../business_process.md)。

## Club Joint Activities — `/clubs/{club_id}/joint-activities`

统一要求**职务: `president`/`vice_president`**（社团管理侧的联合活动全生命周期操作）。下表**错误**列的 `+` 表示"在 `CLUB_NOT_FOUND`/`CLUB_NOT_ACTIVE`（这两个每行都会检查，不重复写）之外，还会有"。

| 方法  | 路径                            | 请求                        | 响应                | 错误                                                                                                          |
| ----- | -------------------------------- | ------------------------------ | ---------------------- | ------------------------------------------------------------------------------------------------------------- |
| GET   | `/`                                | –                                 | `Page[JointActivityInfo]` | `CLUB_NOT_FOUND`, `CLUB_NOT_ACTIVE`                                                                            |
| POST  | `/`                                | `JointActivityCreate`             | `JointActivityInfo`（201）  | `CLUB_NOT_FOUND`, `CLUB_NOT_ACTIVE`                                                                            |
| PATCH | `/{activity_id}`                  | `JointActivityUpdate`             | `JointActivityInfo`         | + `JOINT_ACTIVITY_NOT_FOUND`, `JOINT_ACTIVITY_INITIATOR_REQUIRED`, `JOINT_ACTIVITY_PRELIMINARY_APPROVED`, `JOINT_ACTIVITY_INVALID_TIME_RANGE` |
| POST  | `/{activity_id}/participations`   | –                                 | `JointActivityInfo`（201）  | + `JOINT_ACTIVITY_NOT_FOUND`, `JOINT_ACTIVITY_NOT_PUBLIC`, `JOINT_ACTIVITY_REGISTRATION_CLOSED`, `JOINT_ACTIVITY_CLUB_REGISTERED` |
| PATCH | `/{activity_id}/archive`          | `JointActivityArchiveUpdate`      | `JointActivityInfo`         | + `JOINT_ACTIVITY_NOT_FOUND`, `JOINT_ACTIVITY_INITIATOR_REQUIRED`, `JOINT_ACTIVITY_NOT_PUBLIC`, `JOINT_ACTIVITY_NOT_ENDED`, `JOINT_ACTIVITY_FINAL_REVIEW_LOCKED` |
| POST  | `/{activity_id}/final-submission` | –                                 | `JointActivityInfo`         | 同 `archive` 行 + `JOINT_ACTIVITY_ARCHIVE_REQUIRED`                                                             |

## Star Level — `/star-level`

跨社团只读列表，以及申请人（社长）自助修改。

| 方法  | 路径              | 权限                                      | 请求                       | 响应                              | 错误                                                                 |
| ----- | ------------------ | -------------------------------------------- | ------------------------------ | ------------------------------------ | ------------------------------------------------------------------------- |
| GET   | `/`                  | 公开                                            | –                                 | `Page[StarLevelApplicationPublicInfo]` | –                                                                          |
| GET   | `/{star_level_id}`   | 公开                                            | –                                 | `StarLevelApplicationInfo`             | `STAR_LEVEL_NOT_FOUND`                                                     |
| PATCH | `/{star_level_id}`   | 登录 + 职务: `president`（申请所属社团，手动校验）  | `StarLevelApplicationUpdate`      | `StarLevelApplicationInfo`             | `STAR_LEVEL_NOT_FOUND`, `CLUB_NOT_FOUND`, `CLUB_NOT_ACTIVE`, `CLUB_ROLE_NOT_ALLOWED`, `STAR_LEVEL_UPDATE_DENIED` |

星级评定的**审核**（通过/驳回、给分）在 [Club Federation → Star Level](#star-level--club-federationstar-level)。

## General Activities — `/general-activities`（公开只读）

| 方法 | 路径             | 请求                                                                            | 响应                        | 错误                          |
| ---- | ----------------- | ----------------------------------------------------------------------------------- | ------------------------------ | ------------------------------ |
| GET  | `/{activity_id}`   | –                                                                                      | `GeneralActivityInfo`             | `GENERAL_ACTIVITY_NOT_FOUND`   |
| GET  | `/`                 | Query: `search?`, `level?`, `starts_before?`, `ends_after?`, `has_poster?`               | `Page[GeneralActivityInfo]`       | –                              |

创建/修改/删除见 [Club Federation → General Activities](#general-activities--club-federationgeneral-activity) 和 [Admin → General Activities](#general-activities--admingeneral-activities)。

## Joint Activities — `/joint-activities`（公开只读，仅展示已公开的）

| 方法 | 路径             | 请求               | 响应                          | 错误                     |
| ---- | ----------------- | --------------------- | ------------------------------- | -------------------------- |
| GET  | `/`                 | Query: `search?`         | `Page[JointActivityPublicInfo]`   | –                           |
| GET  | `/{activity_id}`    | –                        | `JointActivityPublicInfo`         | `JOINT_ACTIVITY_NOT_FOUND`  |

## Announcements — `/announcements`（公开只读）

| 方法 | 路径 | 请求                                        | 响应                    | 错误 |
| ---- | ---- | ---------------------------------------------- | -------------------------- | ---- |
| GET  | `/`   | Query: `search?`, `active_only?`（默认 `true`）    | `Page[AnnouncementInfo]`     | –    |

管理端见 [Admin → Announcements](#announcements--adminannouncements)。

## Uploads — `/uploads`

均要求**登录**。详细流程见 [overview.md → 文件上传流程](overview.md#文件上传流程)。

| 方法 | 路径         | 请求                     | 响应                       | 错误                                                                          |
| ---- | ------------- | -------------------------- | ----------------------------- | -------------------------------------------------------------------------------- |
| POST | `/initiate`   | `InitiateUploadRequest`      | `InitiateUploadResponse`（201）  | 原生 `HTTPException`（见[约定](#约定)）：`413` 文件过大 / `400` content-type 或扩展名不支持 |
| POST | `/confirm`    | `ConfirmUploadRequest`       | `ConfirmUploadResponse`          | `UPLOAD_SCENE_MISMATCH`, `UPLOAD_OBJECT_NOT_FOUND`, `UPLOAD_OBJECT_TOO_LARGE`      |

---

## Moderations — `/moderations`

统一要求**角色: `moderator`/`admin`/`dev`**。请求体统一是 `RequestModeratePublic`（`{"moderation_status": "approved"|"rejected"}`，非法值 `INVALID_MODERATION_STATUS`）。

### Users — `/moderations/users`

| 方法  | 路径                        | 请求                  | 响应                              | 错误                                                             |
| ----- | ---------------------------- | ------------------------ | ------------------------------------ | ------------------------------------------------------------------- |
| GET   | `/update-requests`            | –                          | `Page[UserUpdateRequestInfo]`          | –                                                                     |
| PATCH | `/update-requests/{request_id}` | `RequestModeratePublic`    | `UserUpdateRequestInfo`                | `USER_UPDATE_REQUEST_NOT_FOUND`, `USER_UPDATE_REQUEST_MODERATED`, `USER_NOT_FOUND` |

### Club Activities — `/moderations/club-activities`

| 方法  | 路径                                | 请求                  | 响应                                    | 错误                                                                                       |
| ----- | ------------------------------------- | ------------------------ | ------------------------------------------ | ---------------------------------------------------------------------------------------------- |
| GET   | `/create-requests`                     | –                          | `Page[ClubActivityCreateRequestInfo]`         | –                                                                                                |
| PATCH | `/create-requests/{request_id}`        | `RequestModeratePublic`    | `ClubActivityCreateRequestInfo`               | `CLUB_ACTIVITY_CREATE_REQUEST_NOT_FOUND`, `CLUB_ACTIVITY_CREATE_REQUEST_MODERATED`, `CLUB_NOT_FOUND` |
| GET   | `/update-requests`                     | –                          | `Page[ClubActivityUpdateRequestInfo]`         | –                                                                                                |
| PATCH | `/update-requests/{request_id}`        | `RequestModeratePublic`    | `ClubActivityUpdateRequestInfo`               | `CLUB_ACTIVITY_UPDATE_REQUEST_NOT_FOUND`, `CLUB_ACTIVITY_UPDATE_REQUEST_MODERATED`, `CLUB_ACTIVITY_NOT_FOUND`, `CLUB_ACTIVITY_INVALID_TIME_RANGE` |

### Clubs — `/moderations/clubs`

| 方法  | 路径                          | 请求                  | 响应                    | 错误                                                                  |
| ----- | ------------------------------- | ------------------------ | -------------------------- | ------------------------------------------------------------------------ |
| GET   | `/update-requests`               | –                          | `Page[ClubUpdateRequestInfo]` | –                                                                          |
| PATCH | `/update-requests/{request_id}`  | `RequestModeratePublic`    | `ClubUpdateRequestInfo`       | `CLUB_UPDATE_REQUEST_NOT_FOUND`, `CLUB_UPDATE_REQUEST_MODERATED`, `CLUB_NOT_FOUND` |

## Verifications — `/clubs/{club_id}/membership-requests`

统一要求**职务: `president`/`vice_president`**。请求体统一是 `RequestVerifyPublic`（`{"verification_status": "approved"|"rejected"}`，非法值 `INVALID_VERIFICATION_STATUS`）。

| 方法  | 路径             | 请求                  | 响应                              | 错误                                                                                          |
| ----- | ------------------ | ------------------------ | ------------------------------------ | ------------------------------------------------------------------------------------------------- |
| GET   | ``                  | –                          | `Page[ClubMembershipRequestInfo]`      | –                                                                                                   |
| PATCH | `/{request_id}`     | `RequestVerifyPublic`      | `ClubMembershipRequestInfo`            | `CLUB_MEMBERSHIP_REQUEST_NOT_FOUND`, `CLUB_MEMBERSHIP_REQUEST_VERIFIED`, `CLUB_NOT_FOUND`, `CLUB_NOT_ACTIVE`, `USER_NOT_FOUND` |

## Club Federation — `/club-federation`

统一要求**角色: `federation_staff`/`admin`/`dev`**。

### General Activities — `/club-federation/general-activity`

| 方法   | 路径              | 请求                     | 响应                       | 错误                            |
| ------ | ------------------- | -------------------------- | ------------------------------ | --------------------------------- |
| POST   | `/`                   | `GeneralActivityCreate`      | `GeneralActivityInfo`（201）      | `GENERAL_ACTIVITY_INVALID_TIME_RANGE` |
| PATCH  | `/{activity_id}`      | `GeneralActivityUpdate`      | `GeneralActivityInfo`             | `GENERAL_ACTIVITY_NOT_FOUND`, `GENERAL_ACTIVITY_INVALID_TIME_RANGE` |
| DELETE | `/{activity_id}`      | –                             | `GeneralActivityInfo`             | `GENERAL_ACTIVITY_NOT_FOUND`      |

### General Activity Club Records — `/club-federation/general-activity/club-records`

| 方法  | 路径             | 请求                       | 响应                        | 错误                              |
| ----- | ------------------ | ---------------------------- | ------------------------------- | ----------------------------------- |
| PATCH | `/{record_id}`      | `FederationRecordUpdate`       | `ClubGeneralActivityInfo`          | `CLUB_GENERAL_ACTIVITY_RECORD_NOT_FOUND` |

### Star Level — `/club-federation/star-level`

| 方法  | 路径                        | 请求                            | 响应                                | 错误                     |
| ----- | ----------------------------- | ---------------------------------- | -------------------------------------- | --------------------------- |
| POST  | `/{star_level_id}/preview`     | `StarLevelApplicationReview`         | `StarLevelApplicationReviewPreview`      | `STAR_LEVEL_NOT_FOUND`       |
| PATCH | `/{star_level_id}`             | `StarLevelApplicationReview`         | `StarLevelApplicationInfo`               | `STAR_LEVEL_NOT_FOUND`, `CLUB_NOT_FOUND` |

`preview` 不落库，只用来看"按这个审核结果通过会得几分/几星"。

### Joint Activities — `/club-federation/joint-activities`

| 方法  | 路径                                 | 请求                                | 响应                       | 错误                                                          |
| ----- | -------------------------------------- | -------------------------------------- | ------------------------------ | ------------------------------------------------------------------ |
| GET   | `/`                                      | Query: `search?`                          | `Page[JointActivityInfo]`         | –                                                                    |
| PATCH | `/{activity_id}/preliminary-review`      | `JointActivityPreliminaryModeration`      | `JointActivityInfo`               | `JOINT_ACTIVITY_NOT_FOUND`, `JOINT_ACTIVITY_PRELIMINARY_REVIEWED`   |
| PATCH | `/{activity_id}/final-review`            | `JointActivityFinalVerification`          | `JointActivityInfo`               | `JOINT_ACTIVITY_NOT_FOUND`, `JOINT_ACTIVITY_FINAL_REVIEW_NOT_PENDING`, `JOINT_ACTIVITY_INVALID_FINAL_SCORE` |

---

## Admin — `/admin`

统一要求**角色: `admin`/`dev`**。这里的写操作都是**直接生效**，不经过审核流程。

### Users — `/admin/users`

| 方法  | 路径         | 请求                | 响应        | 错误              |
| ----- | -------------- | ---------------------- | ------------- | ------------------- |
| GET   | `/`             | Query: `search?`, `role?` | `Page[UserInfo]` | –                    |
| PATCH | `/{user_id}`    | `AdminUserUpdate`         | `UserInfo`      | `USER_NOT_FOUND`     |

### Clubs — `/admin/clubs`

| 方法  | 路径         | 请求                                         | 响应        | 错误              |
| ----- | -------------- | ----------------------------------------------- | ------------- | ------------------- |
| GET   | `/`             | Query: `search?`, `category?`, `club_status?`      | `Page[ClubInfo]` | –                    |
| GET   | `/{club_id}`    | –                                                  | `ClubInfo`      | `CLUB_NOT_FOUND`     |
| PATCH | `/{club_id}`    | `AdminClubUpdate`（含 `status`、`star_level`）        | `ClubInfo`      | `CLUB_NOT_FOUND`     |

社团 `unreviewed → normal`（审核创建）和 `→ archived`（解散/归档）都通过这个 `PATCH` 完成，见 [../business_process.md](../business_process.md)。

### Academic Terms — `/admin/academic-terms`

| 方法   | 路径                    | 请求                    | 响应              | 错误                     |
| ------ | ------------------------- | -------------------------- | -------------------- | --------------------------- |
| GET    | `/`                         | –                             | `Page[AcademicTermInfo]` | –                            |
| POST   | `/`                         | `AcademicTermCreate`          | `AcademicTermInfo`（201）  | –                            |
| GET    | `/{term_id}`                | –                             | `AcademicTermInfo`       | `ACADEMIC_TERM_NOT_FOUND`     |
| PATCH  | `/{term_id}`                | `AcademicTermUpdate`          | `AcademicTermInfo`       | `ACADEMIC_TERM_NOT_FOUND`     |
| DELETE | `/{term_id}`                | –                             | `AcademicTermInfo`       | `ACADEMIC_TERM_NOT_FOUND`     |
| POST   | `/{term_id}/set-current`    | –                             | `AcademicTermInfo`       | `ACADEMIC_TERM_NOT_FOUND`     |

### General Activities — `/admin/general-activities`

| 方法   | 路径             | 请求                        | 响应                  | 错误                                                     |
| ------ | ------------------ | ------------------------------- | ------------------------ | ------------------------------------------------------------ |
| GET    | `/`                  | Query: `search?`, `level?`         | `Page[GeneralActivityInfo]` | –                                                              |
| POST   | `/`                  | `GeneralActivityCreate`            | `GeneralActivityInfo`（201）  | `GENERAL_ACTIVITY_INVALID_TIME_RANGE`                          |
| PATCH  | `/{activity_id}`     | `GeneralActivityUpdate`            | `GeneralActivityInfo`       | `GENERAL_ACTIVITY_NOT_FOUND`, `GENERAL_ACTIVITY_INVALID_TIME_RANGE` |
| DELETE | `/{activity_id}`     | –                                  | `GeneralActivityInfo`       | `GENERAL_ACTIVITY_NOT_FOUND`                                   |

### Announcements — `/admin/announcements`

| 方法   | 路径                  | 请求                                  | 响应                    | 错误                                                    |
| ------ | ----------------------- | ---------------------------------------- | --------------------------- | ------------------------------------------------------------ |
| GET    | `/`                       | Query: `search?`, `active_only?`（默认 `false`） | `Page[AnnouncementInfo]`      | –                                                              |
| POST   | `/`                       | `AnnouncementCreate`                       | `AnnouncementInfo`（201）       | `ANNOUNCEMENT_INVALID_TIME_RANGE`                              |
| PATCH  | `/{announcement_id}`      | `AnnouncementUpdate`                       | `AnnouncementInfo`             | `ANNOUNCEMENT_NOT_FOUND`, `ANNOUNCEMENT_INVALID_TIME_RANGE`    |
| DELETE | `/{announcement_id}`      | –                                          | `AnnouncementInfo`             | `ANNOUNCEMENT_NOT_FOUND`                                       |

---

## 其它

- `GET /health`（不在 `/api/v1` 前缀下，路径就是 `/health`）：无鉴权存活检查，`204 No Content`，供 Docker healthcheck 使用。
