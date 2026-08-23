# BNDSphere API 参考

所有端点挂载在 `/api/v1` 前缀下（`main.py:31`）。认证通过 `Authorization: Bearer <token>` 头（OAuth2PasswordBearer，`tokenUrl=/api/v1/auth/login`）。

> 交互式文档：启动后端后访问 `/api/docs`（Swagger）或 `/api/redoc`（ReDoc）。

## 认证与用户

### /auth

| 方法 | 路径 | 权限 | 说明 |
| --- | --- | --- | --- |
| POST | `/auth/register` | 公开 | 注册新用户（用户名唯一），返回 `UserInfo` |
| POST | `/auth/login` | 公开 | 用户名+密码登录（OAuth2 表单），返回 JWT `Token` |

### /users

| 方法 | 路径 | 权限 | 说明 |
| --- | --- | --- | --- |
| GET | `/users/me` | 登录 | 获取当前用户公开信息 |
| GET | `/users/{user_id}` | 公开 | 获取指定用户公开信息（不含角色） |
| POST | `/users/update-requests` | 登录 | 申请更新个人信息（待 moderator 审核） |

## 社团

### /clubs

| 方法 | 路径 | 权限 | 说明 |
| --- | --- | --- | --- |
| GET | `/clubs/` | 公开 | 搜索社团（`search`、`category` 过滤，仅 `normal`） |
| POST | `/clubs/` | 登录 | 创建社团（创建者自动成为社长，状态 `unreviewed`） |
| GET | `/clubs/{club_id}` | 公开 | 获取社团信息（仅 `normal` 可见） |
| POST | `/clubs/{club_id}/update-requests` | 社长/副社长 | 申请更新社团信息 |
| POST | `/clubs/{club_id}/membership-requests` | 登录 | 申请加入社团（待社长/副社长审核） |
| DELETE | `/clubs/{club_id}/members/me` | 登录 | 退出社团（社长/副社长不能直接退出） |
| PATCH | `/clubs/{club_id}/members/{user_id}` | 社长 | 任命副社长 / 罢免 / 转让社长 |
| DELETE | `/clubs/{club_id}/members/{user_id}` | 社长 | 移除成员 |

### /clubs/{club_id}/activities（社团活动）

| 方法 | 路径 | 权限 | 说明 |
| --- | --- | --- | --- |
| GET | `/` | 公开 | 获取社团活动列表 |
| POST | `/create-requests` | 社长/副社长 | 申请创建社团活动 |
| POST | `/update-requests/{activity_id}` | 社长/副社长 | 申请修改社团活动 |

## 大型活动

### /general-activities

| 方法 | 路径 | 权限 | 说明 |
| --- | --- | --- | --- |
| GET | `/` | 公开 | 查询大型活动（`search`/`level`/`starts_before`/`ends_after`/`has_poster`） |
| GET | `/{activity_id}` | 公开 | 获取大型活动信息 |

### /clubs/{club_id}/general-activities（社团参与记录）

| 方法 | 路径 | 权限 | 说明 |
| --- | --- | --- | --- |
| GET | `/` | 公开 | 获取社团参与大型活动记录 |
| POST | `/` | 社长/副社长 | 创建参与记录 |
| PATCH | `/` | 社长/副社长 | 编辑参与记录（仅 `pending` 状态） |

## 联合活动

### /joint-activities

| 方法 | 路径 | 权限 | 说明 |
| --- | --- | --- | --- |
| GET | `/` | 公开 | 查询预审通过的联合活动 |
| GET | `/{activity_id}` | 公开 | 获取预审通过的联合活动 |

### /clubs/{club_id}/joint-activities

| 方法 | 路径 | 权限 | 说明 |
| --- | --- | --- | --- |
| GET | `/` | 社长/副社长 | 获取社团的联合活动 |
| POST | `/` | 社长/副社长 | 创建联合活动 |
| PATCH | `/{activity_id}` | 社长/副社长 | 编辑联合活动 |
| POST | `/{activity_id}/participations` | 社长/副社长 | 报名参与联合活动 |
| PATCH | `/{activity_id}/archive` | 社长/副社长 | 更新归档信息 |
| POST | `/{activity_id}/final-submission` | 社长/副社长 | 提交终审 |

## 星级评定 / 星级评分

### /star-level

| 方法 | 路径 | 权限 | 说明 |
| --- | --- | --- | --- |
| GET | `/` | 公开 | 查询所有星级评定申请 |
| GET | `/{star_level_id}` | 公开 | 获取星级评定申请 |
| PATCH | `/{star_level_id}` | 社长 | 更新申请（审核通过后不可改） |

### /clubs/{club_id}/star-level

| 方法 | 路径 | 权限 | 说明 |
| --- | --- | --- | --- |
| GET | `/` | 公开 | 获取社团的星级评定申请 |
| POST | `/` | 社长 | 创建星级评定申请 |

### /clubs/{club_id}/star-rating

| 方法 | 路径 | 权限 | 说明 |
| --- | --- | --- | --- |
| GET | `/` | 公开 | 计算社团星级评分 |

## 管理端

### /admin（需 `admin`/`dev` 角色）

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/admin/users/` | 列出用户（`search`/`role` 过滤） |
| PATCH | `/admin/users/{user_id}` | 编辑用户信息（含角色） |
| GET | `/admin/clubs/` | 列出社团（含 `club_status` 过滤） |
| GET | `/admin/clubs/{club_id}` | 获取社团信息 |
| PATCH | `/admin/clubs/{club_id}` | 编辑社团信息 |
| GET | `/admin/academic-terms/` | 列出学期 |
| POST | `/admin/academic-terms/` | 创建学期 |
| GET | `/admin/academic-terms/{term_id}` | 获取学期 |
| PATCH | `/admin/academic-terms/{term_id}` | 编辑学期 |
| DELETE | `/admin/academic-terms/{term_id}` | 删除学期 |
| POST | `/admin/academic-terms/{term_id}/set-current` | 设为当前学期 |
| GET | `/admin/general-activities/` | 列出大型活动 |
| POST | `/admin/general-activities/` | 创建大型活动 |
| PATCH | `/admin/general-activities/{activity_id}` | 编辑大型活动 |
| DELETE | `/admin/general-activities/{activity_id}` | 删除大型活动 |
| GET | `/admin/announcements/` | 列出公告（`active_only`） |
| POST | `/admin/announcements/` | 创建公告 |
| PATCH | `/admin/announcements/{announcement_id}` | 编辑公告 |
| DELETE | `/admin/announcements/{announcement_id}` | 删除公告 |

## 审核与验证

### /moderations（需 `moderator`/`admin`/`dev` 角色）

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/moderations/users/update-requests` | 待审用户信息更新申请 |
| PATCH | `/moderations/users/update-requests/{request_id}` | 审核用户信息更新申请 |
| GET | `/moderations/clubs/update-requests` | 待审社团信息更新申请 |
| PATCH | `/moderations/clubs/update-requests/{request_id}` | 审核社团信息更新申请 |
| GET | `/moderations/club-activities/create-requests` | 待审社团活动创建申请 |
| PATCH | `/moderations/club-activities/create-requests/{request_id}` | 审核社团活动创建申请 |
| GET | `/moderations/club-activities/update-requests` | 待审社团活动修改申请 |
| PATCH | `/moderations/club-activities/update-requests/{request_id}` | 审核社团活动修改申请 |

### /clubs/{club_id}/membership-requests（需社长/副社长）

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `""`（即 `/clubs/{club_id}/membership-requests`） | 待审加入社团申请 |
| PATCH | `/{request_id}` | 审核（通过/拒绝）加入社团申请 |

## 社联

### /club-federation（需 `federation_staff`/`admin`/`dev` 角色）

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| POST | `/club-federation/general-activity/` | 创建大型活动 |
| PATCH | `/club-federation/general-activity/{activity_id}` | 编辑大型活动 |
| DELETE | `/club-federation/general-activity/{activity_id}` | 删除大型活动 |
| PATCH | `/club-federation/general-activity/club-records/{record_id}` | 审核社团参与记录（定分） |
| POST | `/club-federation/star-level/{star_level_id}/preview` | 预览星级评审结果 |
| PATCH | `/club-federation/star-level/{star_level_id}` | 评审星级评定申请 |
| GET | `/club-federation/joint-activities/` | 列出联合活动（社联视角） |
| PATCH | `/club-federation/joint-activities/{activity_id}/preliminary-review` | 联合活动预审 |
| PATCH | `/club-federation/joint-activities/{activity_id}/final-review` | 联合活动终审 |

## 文件上传

### /uploads（需登录）

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| POST | `/uploads/initiate` | 发起上传，返回 OSS 预签名 PUT URL |
| POST | `/uploads/confirm` | 确认上传，返回可访问 URL |

## 公告

### /announcements

| 方法 | 路径 | 权限 | 说明 |
| --- | --- | --- | --- |
| GET | `/` | 公开 | 首页公告列表（`active_only` 默认 true） |

## 其他

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/health` | 健康检查（204 No Content） |

## 通用约定

- **分页**：列表端点使用 `fastapi-pagination` 的 `Page[T]` 结构（`items` / `total` / `page` / `size`）。
- **错误响应**：业务错误返回统一结构 `{ "message_key", "error_code", "details" }`（见 `main.py` 的 `BusinessError` 处理器）。
- **幂等申请**：同一主体（用户/社团/活动）同一时刻最多存在一条 `pending` 申请，新申请会覆盖旧申请（数据库层用条件唯一索引保证，见 `docs/architecture/database.md`）。
