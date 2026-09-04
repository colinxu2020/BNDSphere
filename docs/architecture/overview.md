# BNDSphere 后端架构概览

> 面向想要理解代码怎么组织、新功能应该加在哪一层的开发者。数据库层面的细节见 [database.md](database.md)，逐接口的行为见 [API.md](API.md)，业务流程的时序描述见 [../business_process.md](../business_process.md)。

## 技术栈

- **框架**：FastAPI，异步全链路（`async def` + SQLAlchemy 2.x 异步引擎 + `psycopg` v3 驱动）
- **数据库**：PostgreSQL（唯一支持的引擎，见 [database.md](database.md)）
- **迁移**：Alembic
- **依赖管理**：`uv`
- **对象存储**：S3 兼容 OSS，通过预签名 URL 直传（见"文件上传"一节）
- **部署单元**：整个后端只有一个 FastAPI 应用（`app/main.py`），不区分微服务；开发/测试/生产都通过 Docker Compose 编排（详见 [../getting-started.md](../getting-started.md)）

## 分层架构

请求经过四层，每一层都对 `[ModelType, CreateSchemaType, UpdateSchemaType]` 泛型：

```
api/v1/*        FastAPI 路由 + Pydantic 请求/响应 schema（schemas/）
   ↓
services/*      ServiceBase 子类：业务规则 + 事务边界
   ↓
repositories/*  RepositoryBase 子类：对 SQLAlchemy 的纯 CRUD 封装
   ↓
models/*        SQLAlchemy Base 子类
```

- **依赖注入**：`api/dependencies.py` 定义了 `ServiceFactory`，一个按请求构造 `Service(Repository(db))` 的通用 FastAPI 依赖，并为每个服务导出一个 `Annotated[..., Depends(...)]` 类型别名（如 `ClubServiceDep`、`StarLevelServiceDep`）。新增接口时通过在这里加一个 `*ServiceDep` 来接线，而不是在路由函数里手动 `Service(Repository(db))`。
- **事务**：`services/unit_of_work.py` 的 `UnitOfWork` 是一个基于 `AsyncSession.info` 深度计数的可重入异步上下文管理器——嵌套的 `async with self.transaction():` 只在最外层提交/回滚。`ServiceBase.create/update/delete` 已经自带事务包装；当一个业务操作需要跨多个仓储原子完成时，在 service 方法里用一个外层 `async with self.transaction():` 把多次仓储调用包起来即可，内层各自的 `create`/`update` 调用不会重复提交。
- **错误**：所有业务失败都是 `services/errors.py` 里 `BusinessError` 的子类（`AuthenticationError`、`BadRequestError`、`ResourceNotFoundError`、`DuplicateResourceError`、`ResourceForbiddenError`、`BusinessPermissionError`…），每个都带一个 HTTP 状态码、一个 i18n 用的 `message_key`、一个机器可读的 `error_code`，以及可选的 `details`。`app/main.py` 里的一个统一异常处理器把它们转成 `{message_key, error_code, details}` 的 JSON 响应。前端在 `frontend/src/lib/labels.ts`（`ERROR_CODE_MESSAGES`）里把 `error_code` 映射成中文文案——新增错误码时也要同步在那里补一条。
- **访问控制**：`services/policies.py` 的 `AccessPolicy` 是角色/成员资格检查的唯一权威实现：
  - `ensure_user_active`：`role=ban` 的用户一律拒绝。
  - `ensure_role_allowed`：检查全局角色（`RoleEnum`）是否在允许列表里；`RoleEnum.dev` 对所有此类检查免检。
  - `ensure_club_role_allowed`：检查用户在某个社团里的职务（`ClubMembershipEnum`）；`admin`/`dev` 对所有社团职务检查免检。
  `api/dependencies.py` 的 `RoleChecker` / `ClubRoleChecker` 是把上面两个方法包成 FastAPI 依赖，挂在路由或路由组的 `dependencies=[...]` 上；新路由应复用它们，而不是在业务代码里手写角色判断。
- **配置**：`core/settings.py` —— `WebSettings` / `DatabaseSettings` / `OSSSettings`（基于 `pydantic-settings`，`secrets_dir=/run/secrets`，用 `@cache` 缓存单例）。开发/测试环境下的值来自 Docker secrets（`scripts/gen-secrets.sh` 生成、Compose 挂载），不是应用自己去读某个 `.env` 文件。
- **数据库约定**：`core/database.py` 的 `Base` 把所有表固定在 Postgres 的 `app` schema 下，并通过 `MetaData(naming_convention=...)` 统一了约束/索引命名（`ix_/uq_/ck_/fk_/pk_<table>_<cols>`）——新模型应该依赖这套约定，而不是手写约束名。

## 审核 / 核验模式（Moderation / Verification）

很多写操作不是直接生效，而是先落一条"待审核"记录，由有权限的人审核通过后才应用到目标表：

- **Moderation**（`models/moderations/`）：`ClubUpdateRequest`、`ClubActivityCreateRequest`、`ClubActivityUpdateRequest`、`UserUpdateRequest`。都混入 `ModerationMixin`（`moderation_status: pending|approved|rejected|superseded`、`moderator_id`、`moderate_at`）和 `RequestorMixin`（`requestor_id`、`request_at`），定义在 `models/moderations/moderation_common.py`。路由挂在 `api/v1/moderations/` 下，统一要求 `moderator`/`admin`/`dev` 角色。同一目标上新提交一个待审核请求，会先把该目标上已有的 pending 请求置为 `superseded`（见各 `supersede_pending_requests_by_*` 方法），保证同一时刻至多一条 pending 请求（由条件唯一索引兜底）。
- **"简单审核流"**（`AuditMixin`，定义在 `models/user.py`，被 `club_general_activity_records` 和 `star_level_applications` 使用）：不单独建申请表，记录本身就带 `audit_status: pending|approved|rejected` + `auditor_id` ——因为这些记录本来就是"要审核的申请"，没有"先写正式表、审核后再写另一张表"的必要。
- **Verification**（`models/verifications/`）：例如社团加入申请 `ClubMembershipRequest`（`ClubMembershipEnum.pending` → 由社长/副社长核验）。路由挂在 `api/v1/verifications/` 下。
- **联合活动**（`models/joint_activity.py`）的初审/终审是第三种变体：状态字段（`preliminary_status`、`final_status`）直接写在 `JointActivity` 上（分别复用 `ModerationStatusEnum`/`VerificationStatusEnum`），但活动本身不是"申请表"——它既是被审核的对象，也是最终生效的记录。
- `services/moderation_payload.py` 提供两个共享辅助：`requested_update_fields(payload)`（从提交的 Pydantic payload 里提取"用户实际填写了哪些字段"，排除系统字段）、`build_update_payload(request, schema_type)`（把一条审核通过的申请记录，按 `update_fields`（没有则按"非空字段"）拼成目标表的 Update Schema）。新增审核类字段/动作时先看是否能复用这套逻辑，而不是手写局部更新。

加新的审核类字段/动作时，先判断它更接近上面哪一种形状（有没有独立申请表？谁来审？一次能不能有多条 pending？），再决定要不要真的发明一种新形状。

## 领域概览

完整的表结构（所有表、枚举、关系、ER 图）见 [database.md](database.md)，不在这里重复推导。核心实体：

| 领域         | 核心表 / 概念                                                                 |
| ------------ | ------------------------------------------------------------------------------ |
| 用户         | `users`（角色 `ban/user/moderator/federation_staff/admin/dev`，年级 `grade`）  |
| 社团         | `clubs`（状态 `unreviewed/normal/archived`，星级，分类，标签）、`club_members`（职务 `pending/member/president/vice_president/left`） |
| 社团活动     | `club_activities` + `club_activity_create_requests`/`club_activity_update_requests`（审核制） |
| 学期         | `academic_terms`（有且仅有一个"当前学期"，靠部分唯一索引保证）                |
| 校级/大型活动 | `general_activities` + `club_general_activity_records`（`AuditMixin`），附带 `activity_conditions`/`record_condition_details`（目前尚无对应 API） |
| 联合活动     | `joint_activities` + `joint_activity_participations`：发起 → 社联初审公开 → 社团报名 → 结项归档 → 终审打分 |
| 星级评定     | `star_level_applications`（`AuditMixin`）+ `StarRatingService` 的实时评分算法  |
| 公告         | `announcements`，按 `is_active` + 时间窗口对外展示                            |
| 文件上传     | 无独立表；`uploads` 路由 + `services/upload_policy.py` 按"场景"校验大小/类型/扩展名，走 OSS 预签名 URL 直传 |

角色相关的一个重要更正：全局角色**没有** "社联/union of associations" 这个值——社联相关权限走的是 `RoleEnum.federation_staff`；社团内部职务用的是 `vice_president`（下划线），不是 "vice president"（空格）。

## 文件上传流程

`POST /uploads/initiate` → 前端直传 OSS → `POST /uploads/confirm`：

1. `initiate`：根据 `scene`（`avatar`/`club_logo`/`activity_poster`/`application_file`/`joint_activity_archive`，见 `schemas/upload.py::UploadScene`）查出对应的 `UploadPolicy`（最大体积、允许的 content-type/扩展名、OSS 目录、URL 有效期），校验客户端声明的大小/类型/扩展名，生成一个带过期时间的 PUT 预签名 URL。
2. 前端直接 PUT 到 OSS，不经过后端。
3. `confirm`：用 OSS 的 HEAD 请求取回**服务端记录的实际大小**（而不是客户端上报的 `size`——预签名 URL 本身不限制真实上传体积，所以这一步是防止绕过 `initiate` 阶段大小校验的关键），校验通过后返回可公开访问的 URL（`oss_public_base_url` + object key）。

只有登录用户可以发起（`Depends(get_current_user)`），没有额外的角色限制。

## 相关文档

- [database.md](database.md) —— 完整表结构、枚举、ER 图
- [API.md](API.md) —— 按路由分组的接口清单（鉴权要求、路径、行为摘要）
- [../business_process.md](../business_process.md) —— 关键业务流程的时序描述（社团创建、成员加入/退出、活动发布、星级评定……）
- [../getting-started.md](../getting-started.md) —— 本地开发环境搭建、测试、代码检查
