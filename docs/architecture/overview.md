# BNDSphere 系统总览

BNDSphere 是 BNDS 社团管理平台，覆盖**用户、社团、活动、审核、星级评定、学期、公告、文件上传**等业务域。

## 架构分层

后端采用分层架构，主调用链依赖方向自上而下（见下图）；并非严格禁止跨层——路由层会直接导入 ORM 模型（用于类型标注/响应校验），`api/dependencies.py` 作为组合根统一导入并实例化仓储与服务（依赖注入）。主调用链：

```
api/v1 (路由) → schemas (请求/响应) → services (业务逻辑) → repositories (数据访问) → models (ORM)
```

| 层 | 目录 | 职责 |
| --- | --- | --- |
| 路由层 | `backend/app/api/v1/` | 定义 HTTP 端点、鉴权、参数校验、响应模型 |
| Schema 层 | `backend/app/schemas/` | Pydantic 请求/响应模型 |
| 服务层 | `backend/app/services/` | 业务规则、权限策略（`policies.py`）、事务边界 |
| 仓储层 | `backend/app/repositories/` | SQLAlchemy 查询封装 |
| 模型层 | `backend/app/models/` | ORM 模型与枚举（含 `moderations/`、`verifications/` 子包） |

## 功能子域

### 用户（User）
- 注册、登录（JWT OAuth2 Bearer）
- 获取当前用户 / 指定用户公开信息
- 申请更新个人信息（经 moderator 审核后生效）

### 社团（Club）
- 创建社团（创建者自动成为社长，初始状态 `unreviewed`，需 admin 审核）
- 搜索 / 查询社团（仅 `normal` 状态公开可见）
- 申请更新社团信息（社长/副社长发起，经 moderator 审核）
- 加入 / 退出社团（加入需社长/副社长审核）
- 成员管理：任命/罢免副社长、转让社长、移除成员（仅社长）

### 社团活动（Club Activities）
- 获取社团活动列表
- 申请创建 / 申请修改社团活动（社长/副社长发起，经 moderator 审核）
- 活动参与者记录（`club_activity_participants` 关联表）

### 大型活动（General Activities）
- 公开查询 / 获取大型活动
- admin 或社联（federation_staff）创建 / 编辑 / 删除大型活动

### 社团参与大型活动记录（Club General Activities）
- 社团创建 / 编辑参与大型活动的记录（社长/副社长，仅 `pending` 可编辑）
- 社联审核记录并给出最终分数（`final_score`）

### 联合活动（Joint Activities）
- 社团发起联合活动，公开查询（仅预审通过的可见）
- 社团侧：创建 / 编辑 / 报名参与 / 归档 / 提交终审
- 社联侧：预审（preliminary-review）+ 终审（final-review）

### 星级评定（Star Level）
- 社团创建星级评定申请（社长，每学期每社团一次）
- 公开查询 / 更新申请（审核通过后不可改）
- 社联评审（preview + review）

### 星级评分（Star Rating）
- 社团实时计算星级评分

### 审核（Moderation）
- moderator/admin/dev 审核：
  - 用户信息更新申请（`user_update_requests`）
  - 社团信息更新申请（`club_update_requests`）
  - 社团活动创建申请（`club_activity_create_requests`）
  - 社团活动修改申请（`club_activity_update_requests`）

### 验证（Verification）
- 社长/副社长审核加入社团申请（`club_membership_requests`）

### 学期（Academic Terms）
- 仅 admin：创建 / 读取 / 编辑 / 删除学期、设置当前学期

### 公告（Announcements）
- 首页公开查询（`active_only` 默认 true）
- admin 增删改

### 文件上传（Uploads）
- 登录用户：发起上传（换取预签名 URL）+ 确认上传（换取可访问 URL）

## 角色体系

### 全局角色（`RoleEnum`）

| 角色 | 值 | 说明 |
| --- | --- | --- |
| 封禁 | `ban` | 被封禁用户 |
| 普通用户 | `user` | 默认角色 |
| 审核员 | `moderator` | 审核各类申请 |
| 社联成员 | `federation_staff` | 管理大型活动、联合活动、星级评定 |
| 管理员 | `admin` | 全局管理（用户、社团、学期、公告、大型活动） |
| 开发者 | `dev` | 拥有 admin + 审核 + 社联全部权限 |

### 社团成员角色（`ClubMembershipEnum`）

| 角色 | 值 | 说明 |
| --- | --- | --- |
| 待审核 | `pending` | 申请加入待审 |
| 成员 | `member` | 普通成员 |
| 社长 | `president` | 最高权限（成员管理、星级申请） |
| 副社长 | `vice_president` | 与社长共享大部分管理权限 |
| 已退出 | `left` | 已退出社团 |

## 权限矩阵

| 操作 | 匿名 | user | 社长/副社长 | 社长 | moderator | federation_staff | admin | dev |
| --- | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: |
| 注册 / 登录 | ✓ | | | | | | | |
| 获取当前用户信息 | | ✓ | | | | | | |
| 申请更新个人信息 | | ✓ | | | | | | |
| 查询社团 / 大型活动 / 联合活动 / 星级申请 / 公告 | ✓ | | | | | | | |
| 创建社团 | | ✓ | | | | | | |
| 加入 / 退出社团 | | ✓ | | | | | | |
| 更新社团信息（申请） | | | ✓ | | | | ✓ | ✓ |
| 创建/修改社团活动（申请） | | | ✓ | | | | ✓ | ✓ |
| 创建/编辑参与大型活动记录 | | | ✓ | | | | ✓ | ✓ |
| 创建联合活动 / 报名 / 归档 / 终审提交 | | | ✓ | | | | ✓ | ✓ |
| 审核加入社团申请 | | | ✓ | | | | ✓ | ✓ |
| 成员管理（任命/移除/转让） | | | | ✓ | | | ✓ | ✓ |
| 创建星级评定申请 | | | | ✓ | | | ✓ | ✓ |
| 更新星级评定申请（未审） | | | | ✓ | | | ✓ | ✓ |
| 文件上传（预签名） | | ✓ | | | | | | |
| 审核各类申请（用户/社团/活动） | | | | | ✓ | | ✓ | ✓ |
| 管理大型活动 / 联合活动 / 星级评审 | | | | | | ✓ | ✓ | ✓ |
| 管理用户 / 社团 / 学期 / 公告 | | | | | | | ✓ | ✓ |

## 附录

- SCF：Staff of Club Federation（社联成员）
- 所有权限校验集中在 `backend/app/api/dependencies.py` 的 `RoleChecker`（全局角色）与 `ClubRoleChecker`（社团成员角色），策略判定见 `backend/app/services/policies.py`。
