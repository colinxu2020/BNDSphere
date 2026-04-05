# 数据库架构

本文档基于 `backend/app/models` 中的 SQLAlchemy 模型，概述当前后端的数据表、字段、关联关系和主要约束。

## 1. 设计概览

当前数据库以以下核心实体为中心：

- `users`：用户基础信息和权限角色
- `clubs`：社团信息
- `club_members`：用户与社团的成员关系
- `tags`：社团标签
- `activities`：社团活动
- `club_tags`：社团与标签的多对多关联表
- `activity_participators`：活动与参与用户的多对多关联表

### 统一约定

- 所有主表都继承自 `app.core.database.Base`。
- 主键 `id` 来自公共基类，模型文件中未重复声明。
- 所有时间字段使用 `DateTime(timezone=True)`。
- 创建时间通常由数据库侧 `server_default=func.now()` 生成。
- 枚举字段使用 Python `StrEnum`，数据库中按字符串值保存。
- 文本搜索和唯一性约束主要围绕社团与活动的名称字段展开。

## 2. 实体表

### 2.1 `users`

用户表，存储账号、展示信息和角色信息。

| 字段 | 类型 | 约束 / 默认值 | 说明 |
| --- | --- | --- | --- |
| `username` | `Text` | `unique=True`, `index=True` | 用户名 |
| `email` | `Text` | `unique=True`, `default=None` | 邮箱，可为空 |
| `hashed_password` | `String(255)` | 必填 | 加密后的密码 |
| `avatar_uri` | `HttpUrlType` | `default=None` | 头像链接，可为空 |
| `description` | `Text` | 默认 `这位用户还没有设置简介` | 用户简介 |
| `real_name` | `String(20)` | `default=None` | 真实姓名，可为空 |
| `role` | `RoleEnum` | 默认 `user` | 用户角色 |
| `wecom_userid` | `String(64)` | `unique=True`, `index=True`, `default=None` | 企业微信用户 ID，可为空 |
| `created_at` | `DateTime(timezone=True)` | `server_default=func.now()` | 创建时间 |

#### `RoleEnum`

- `ban`
- `user`
- `union of associations`
- `admin`
- `dev`

#### 关系

- `club_memberships` -> `club_members`
- `participated_activities` -> `activity_participators`

---

### 2.2 `clubs`

社团主表，保存社团基础资料、审核状态和分类信息。

| 字段 | 类型 | 约束 / 默认值 | 说明 |
| --- | --- | --- | --- |
| `name` | `String(settings.club_max_name_length)` | `index=True` | 社团名称 |
| `summary` | `Text` | 必填 | 简介摘要 |
| `description` | `Text` | 必填 | 详细介绍 |
| `logo_uri` | `HttpUrlType` | `default=None` | Logo 链接，可为空 |
| `created_at` | `DateTime(timezone=True)` | `server_default=func.now()` | 创建时间 |
| `status` | `ClubStatusEnum` | 默认 `unreviewed` | 审核状态 |
| `star_level` | `ClubStarLevelEnum` | 默认 `none` | 星级等级 |
| `category` | `ClubCategoryEnum` | 必填 | 社团分类 |

#### `ClubStatusEnum`

- `unreviewed`
- `normal`
- `archived`

#### `ClubStarLevelEnum`

- `none`
- `one_star`
- `two_star`
- `three_star`
- `four_star`
- `five_star`
- `honorary`

#### `ClubCategoryEnum`

- `sports`
- `humanity`
- `arts`
- `science`
- `charity`
- `business`
- `campus`
- `other`

#### 索引与约束

- `ix_unique_active_club_name`
  - 仅对未归档社团生效的唯一索引
  - 使用条件表达式 `status != archived`
  - 目的：允许已归档社团重名，但保证活跃社团名称唯一
- `ix_clubs_name_trgm`
  - 社团名称搜索索引
- `ix_clubs_summary_trgm`
  - 社团摘要搜索索引
- `ix_clubs_description_trgm`
  - 社团描述搜索索引

#### 关系

- `members` -> `club_members`
- `tags` -> `club_tags`
- `activities` -> `activities`

---

### 2.3 `club_members`

用户与社团的成员关系表，用于描述用户在社团中的身份。

| 字段 | 类型 | 约束 / 默认值 | 说明 |
| --- | --- | --- | --- |
| `user_id` | `ForeignKey("users.id")` | 必填 | 关联用户 |
| `club_id` | `ForeignKey("clubs.id")` | 必填 | 关联社团 |
| `membership` | `ClubMembershipEnum` | 必填 | 成员身份 |
| `updated_at` | `DateTime(timezone=True)` | `server_default=func.now()`, `onupdate=func.now()` | 最后更新时间 |

#### `ClubMembershipEnum`

- `none`
- `pending`
- `member`
- `president`
- `vice`（枚举值字符串为 `vice president`）

#### 约束

- `UniqueConstraint("club_id", "user_id")`
  - 同一用户在同一社团中只能有一条成员记录

#### 关系

- `user` -> `users`
- `club` -> `clubs`

---

### 2.4 `tags`

标签表，用于给社团打标签。

| 字段 | 类型 | 约束 / 默认值 | 说明 |
| --- | --- | --- | --- |
| `name` | `String(settings.tag_max_name_length)` | `unique=True`, `index=True` | 标签名称 |
| `status` | `TagStatusEnum` | 默认 `normal` | 标签状态 |

#### `TagStatusEnum`

- `normal`
- `archived`

#### 关系

- `clubs` -> `club_tags`

---

### 2.5 `activities`

活动表，描述社团发布的活动信息。

| 字段 | 类型 | 约束 / 默认值 | 说明 |
| --- | --- | --- | --- |
| `name` | `String(settings.activity_max_name_length)` | `index=True` | 活动名称 |
| `description` | `Text` | 必填 | 活动详情 |
| `club_id` | `ForeignKey("clubs.id")` | 必填 | 所属社团 |
| `start_time` | `DateTime(timezone=True)` | 必填 | 开始时间 |
| `end_time` | `DateTime(timezone=True)` | 必填 | 结束时间 |
| `status` | `ActivityStatusEnum` | 默认 `upcoming` | 活动状态 |

#### `ActivityStatusEnum`

- `upcoming`
- `ongoing`
- `completed`
- `cancelled`

#### 关系

- `club` -> `clubs`
- `participators` -> `activity_participators`

## 3. 关联表

### 3.1 `club_tags`

社团与标签的多对多关联表。

| 字段 | 类型 | 约束 |
| --- | --- | --- |
| `club_id` | `ForeignKey("clubs.id")` | 主键的一部分 |
| `tag_id` | `ForeignKey("tags.id")` | 主键的一部分 |

#### 说明

- 这是纯关联表，不包含额外业务字段。
- 每个 `(club_id, tag_id)` 组合唯一。

---

### 3.2 `activity_participators`

活动与参与用户的多对多关联表。

| 字段 | 类型 | 约束 |
| --- | --- | --- |
| `user_id` | `ForeignKey("users.id")` | 主键的一部分 |
| `activity_id` | `ForeignKey("activities.id")` | 主键的一部分 |

#### 说明

- 这是纯关联表，不包含额外业务字段。
- 每个 `(user_id, activity_id)` 组合唯一。

## 4. 关系总览

- 一个 `User` 可以拥有多条 `ClubMember` 记录。
- 一个 `Club` 可以拥有多条 `ClubMember` 记录。
- 一个 `Club` 可以关联多个 `Tag`，一个 `Tag` 也可以关联多个 `Club`。
- 一个 `Club` 可以拥有多个 `Activity`。
- 一个 `Activity` 可以有多个参与者 `User`。
- 一个 `User` 可以参与多个 `Activity`。

## 5. 索引与查询优化

当前模型中已有的主要查询优化点：

- `users.username`：用户登录/检索
- `users.wecom_userid`：企业微信绑定检索
- `clubs.name`：社团名检索
- `clubs.summary` / `clubs.description`：全文或模糊搜索
- `activities.name`：活动名检索
- `tags.name`：标签检索

其中社团字段的三组搜索索引兼容 PostgreSQL 与 MySQL 的不同实现方式。

## 6. 说明与约定

1. 本文档仅描述当前模型代码体现的结构，不推断未在模型中显式定义的业务规则。
2. `updated_at` 目前只出现在 `club_members`，说明成员身份变更会记录最后更新时间。
3. 活动时间区间是否允许交叉、结束时间是否必须晚于开始时间，当前模型层未做约束，通常需要在业务层校验。
4. 归档状态仅在 `clubs` 与 `tags` 中出现，表示这些对象可能保留历史数据但不再参与正常展示或检索。
