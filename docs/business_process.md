# 业务流程

> 按当前后端实现（`backend/app/services/`、`backend/app/api/v1/`）整理的关键业务流程时序。角色/术语定义见 [architecture/overview.md](architecture/overview.md) 与 [architecture/database.md](architecture/database.md)；每个流程对应的具体接口见 [architecture/API.md](architecture/API.md)。
>
> 标记为 **尚未实现** 的小节描述的是模型/常量已经就位、但目前没有对应 API 或校验逻辑的设想；标记为 **设计待定** 的是代码里还没有答案的开放问题，照抄旧版本文档的原始提问，避免误导为"已实现的规则"。

## user

### 用户注册

`POST /auth/register`：任何人可注册，`username` 全局唯一，冲突返回 `409`。密码用 argon2 哈希存储。注册不需要审核，创建后即为 `role=user`，可直接 `POST /auth/login` 登录。

### 用户信息更新

用户对自己资料的修改是审核制（moderation）：

1. 用户 `POST /users/update-requests` 提交想改的字段（`username`/`avatar_uri`/`description`/`grade`，只填要改的）。同一用户此前若还有一条 pending 的申请，会被自动标记为 `superseded`（不会报错，新申请直接顶替旧的）。
2. `moderator`/`admin`/`dev` 通过 `GET /moderations/users/update-requests` 看到待审列表，`PATCH /moderations/users/update-requests/{id}` 通过或驳回。
3. 通过时，只有申请里实际提交的那些字段会被写回 `users` 表（其余字段不受影响）。

> 站内信/推送通知目前不在后端范围内——以上"推送/通知"步骤是产品设计意图，不是本仓库已实现的功能；仓库里没有消息/通知相关的模型或服务。下文所有流程同理，不再逐条重复这个说明。

## club

### 社团创建

`POST /clubs/`：登录用户直接提交即创建，**没有管理员审核这一步**——创建者立刻成为 `president`，社团状态默认为 `unreviewed`。社团名在所有未归档（`status != archived`）的社团里必须唯一，重名 `409`。

`unreviewed` → `normal` 的状态流转目前只能由 `admin`/`dev` 通过 `PATCH /admin/clubs/{club_id}` 手动完成（把 `status` 改成 `normal`），没有独立的"审核创建申请"接口或队列——`status` 本身就是审核结果的载体。多数面向普通用户的接口（获取详情、加入、发活动……）都要求 `status=normal`，否则 `403 CLUB_NOT_ACTIVE`。

### 社团解散/归档

同样只能由 `admin`/`dev` 通过 `PATCH /admin/clubs/{club_id}` 把 `status` 改为 `archived` 完成；**没有**面向社长自助解散的接口。归档后：

- 社团名唯一性约束自动解除（`ix_unique_active_club_name` 只约束非归档社团），允许新社团复用同名。
- 社团及其成员、活动记录等关联数据都不会被物理删除。

### 社员的加入与离开

**加入**（verification 流程）：

1. 用户 `POST /clubs/{club_id}/membership-requests` 提交申请（附言 `message`）。若该用户在此社团已有非 `left` 的成员记录（已是成员/已在申请中），返回 `409`。
2. 社长/副社长 `GET /clubs/{club_id}/membership-requests` 看到待处理列表，`PATCH /clubs/{club_id}/membership-requests/{id}` 通过或驳回。
3. 通过时，系统直接把申请人写入 `club_members`（`membership=member`）。

**离开**：`DELETE /clubs/{club_id}/members/me`。系统检查发起者的职务：若是 `president` 或 `vice_president` 直接拒绝（`403`，需要先被转让/罢免职务才能退出）；否则把 `membership` 置为 `left`（软删除——参与/举办活动的历史记录不受影响，行保留在 `club_members` 里）。

**社长操作成员**：`PATCH /clubs/{club_id}/members/{user_id}` 任命/罢免副社长，或把社长职位转让给目标成员（转让后操作者自己降为普通成员）；`DELETE /clubs/{club_id}/members/{user_id}` 由社长移出成员（同样是软删除），但不能移除社长自己。

### 社团基础信息更新

审核制（moderation），流程与"用户信息更新"结构一致：

1. 社长/副社长 `POST /clubs/{club_id}/update-requests` 提交想改的字段（`summary`/`description`/`logo_uri`）。同一社团若已有 pending 申请，自动被新申请顶替（`superseded`）。
2. `moderator`/`admin`/`dev` 通过 `GET /moderations/clubs/update-requests` / `PATCH /moderations/clubs/update-requests/{id}` 审核。
3. 通过后只更新申请里实际提交的字段。

`status`（含"审核通过创建申请"）和 `star_level` 不走这条审核通道——前者是管理员职权（见上），后者由星级评定流程写回（见下文）。

### 社团活动

社团活动的创建与修改都是审核制（moderation），没有"直接发布"的接口：

#### 发布（新建）

1. 社长/副社长 `POST /clubs/{club_id}/activities/create-requests` 提交完整的活动信息（名称、描述、地点、起止时间）。
2. `moderator`/`admin`/`dev` 通过 `GET /moderations/club-activities/create-requests` / `PATCH /moderations/club-activities/create-requests/{id}` 审核。
3. 通过后在 `club_activities` 表新建一行。

> 旧版文档提到过"发布申请应在活动开始前一日 21:00 前提交""是否需要单独设置审核员角色"等设计问题——代码里**没有**任何时间截止校验，审核角色就是通用的 `RoleEnum.moderator`（以及 `admin`/`dev`），不区分"社联人员是否可审"。这两点目前仍是设计待定，不是已落地的规则。

#### 修改

社长/副社长 `POST /clubs/{club_id}/activities/update-requests/{activity_id}` 提交要改的字段（只填要改的），同一活动若已有 pending 修改申请会被顶替；若修改涉及起止时间，最终生效的起止时间（结合未修改的原值）必须合法，否则 `400`。审核流程与新建相同，通过后局部更新目标活动。

#### 取消 / 补发布 / 签到 / 活动信息提交（图文素材） — **尚未实现**

旧版文档设想的"取消活动""活动结束后补发布""社长录入/扫码签到""活动结束后提交图文材料再审核"等能力，在当前代码里没有对应的接口或状态字段——`club_activities` 只有一次性的"创建 → （可多次）修改"两个动作，没有取消/签到/结项这些子状态。`picture_urls` 字段存在（活动图片列表），但只能通过"修改活动"申请整体替换，没有独立的"活动信息提交并二次审核"流程。

### 参与大型活动（校级/社联通用活动）

面向单个社团参与校级/大型活动的记录：

1. 社长/副社长 `POST /clubs/{club_id}/general-activities`，选择一个已有的 `general_activities` 记录，附上参与类型（`participate_only`/`organize`）、申请分数、证明材料。同一社团对同一活动只能提交一条，重复 `409`。
2. 该记录默认 `audit_status=pending`；在被审核前，社长/副社长可以 `PATCH /clubs/{club_id}/general-activities` 修改，一旦审核完成（非 `pending`）则不可再改（`403`）。
3. 社联侧（`federation_staff`/`admin`/`dev`）通过 `PATCH /club-federation/general-activity/club-records/{record_id}` 给出 `final_score` 并把 `audit_status` 置为 `approved`/`rejected`。通过的 `final_score` 会计入该社团的星级评分（见下文"社团星级评分"）。

校级/大型活动本身（`general_activities` 记录，含名称、级别、时间、海报）由社联或管理员在 [Club Federation → General Activities](architecture/API.md#general-activities-1) / [Admin → General Activities](architecture/API.md#general-activities-2) 维护，普通用户/社团只读（`GET /general-activities`）。

### 联合活动（跨社团活动）

面向"多个社团联合举办一场活动"的完整流程，比旧版文档设想的"参与大型活动"更完整地落地为代码：

```
发起(pending) --社联初审--> 公开可报名(approved) --社团报名(可多个)--> 活动结束
                                                                        │
                                                              发起社团填写结项材料
                                                                        │
                                                              提交终审(final:pending)
                                                                        │
                                                          社联终审打分(6~8分, approved/rejected)
```

1. **发起**：社团社长/副社长 `POST /clubs/{club_id}/joint-activities/`（`club_id` = 发起社团），初始 `preliminary_status=pending`。
2. **初审**：社联 `PATCH /club-federation/joint-activities/{id}/preliminary-review` 决定是否公开。只能对 `pending` 的活动操作一次；通过后活动才会出现在公开列表 `GET /joint-activities/`。
3. **修改**：初审通过前，发起社团可以 `PATCH /clubs/{club_id}/joint-activities/{id}` 修改活动信息；修改会把初审状态重置回 `pending`（需要重新走一遍初审）。初审通过后禁止再改。
4. **报名**：初审通过、活动尚未结束时，任意社团（含发起社团自己）的社长/副社长可 `POST /clubs/{club_id}/joint-activities/{id}/participations` 为本社团报名；每个社团对同一活动只能报名一次。
5. **结项归档**：活动结束后，发起社团 `PATCH /clubs/{club_id}/joint-activities/{id}/archive` 填写结项文字/材料（可反复修改，直到提交终审）。
6. **提交终审**：发起社团 `POST /clubs/{club_id}/joint-activities/{id}/final-submission`，要求结项文字或材料至少有一项，否则 `400`；提交后 `final_status=pending`。
7. **终审**：社联 `PATCH /club-federation/joint-activities/{id}/final-review` 给出 `final_score`（`approved` 时必须落在 `[6, 8]` 分区间）并决定 `approved`/`rejected`。

### 社团星级评价

社团的综合星级由两部分构成：

1. **实时评分**（`GET /clubs/{club_id}/star-rating`）：任何人可查询，基于当前学期的公开数据（社联例会出勤、活动参与、校内活动次数、成长故事、跨年级影响力、社团年龄）实时算出的一个"参考分"，**不落库、不直接影响 `clubs.star_level`**。
2. **正式评定**（星级评定申请）：
   1. 社长 `POST /clubs/{club_id}/star-level/` 提交本学期的星级评定申请（竞赛附件、竞赛自报分数、独特性声明、成长故事材料、跨年级目标级部）。同一社团同一学期只能有一条申请。
   2. 通过前，社长可以 `PATCH /star-level/{id}` 修改申请内容；社联可以先 `POST /club-federation/star-level/{id}/preview` 预览"如果这样审会得多少分/几星"（不落库）。
   3. 社联正式审核 `PATCH /club-federation/star-level/{id}`：给出竞赛终审分、独特性/成长故事是否通过。若 `audit_status=approved`，系统重新计算总分与星级，写回该申请的 `approved_score`/`approved_level`，**并把结果写入 `clubs.star_level`**（这是 `clubs.star_level` 唯一的写入路径）。

评分算法（`StarRatingService._calculate_score`，满分 100，超过按 100 计）：

| 项目                                   | 分值来源                                                                                   |
| ---------------------------------------- | --------------------------------------------------------------------------------------------- |
| 社联例会出勤                             | 本学期有任意"社联参与"记录即得 10 分，否则 0 分                                              |
| 活动参与 + 竞赛（合计上限 45 分）         | 竞赛分取自已通过的星级评定申请（`final_contest_score`，参与本次评审时用预览值）；活动参与分取自本学期已审核通过的 `club_general_activity_records.final_score` 总和；两者相加封顶 45，竞赛优先计入 |
| 校内活动次数                             | 按本学期"内部活动"数量分档：≥15 次 30 分 / ≥10 次 20 分 / ≥5 次 10 分 / ≥3 次 3 分 / 否则 0 分 |
| 特色加分（合计上限 10 分）                | 成长故事通过 +5；跨年级影响力（若申请设置了目标级部，目标级部成员数 ≥25 得 5 分；否则要求成员覆盖全部 6 个年级才得 5 分）+5；社团成立满 2 年 +5 |

总分对照星级：`≥90` 特别荣誉，`≥80` 五星，`≥70` 四星，`≥50` 三星，`≥30` 二星，`≥10` 一星，否则无星级。

## club federation

### 大型活动

见上文"参与大型活动（校级/社联通用活动）"与"联合活动（跨社团活动）"——两者对应的模型不同（`general_activities` vs `joint_activities`），旧版文档统称的"大型活动"在当前实现里是两条独立的功能线。

### 社团星级评级

见上文"社团星级评价"。

## misc

### 企业微信集成 / 毕业处理 — **设计待定**

`users.wecom_userid` 字段已经存在（唯一索引），但当前代码里**没有**任何企业微信 OAuth 登录、身份绑定或毕业清退的实现——`POST /auth/login` 只支持用户名密码登录。"用企业微信认定，毕业的人怎么处理"仍是未解决的产品问题，照抄自旧版文档，供后续设计参考。

### 通知 / 站内信 — **尚未实现**

以上流程里提到的"推送站内信"均为产品设计意图；仓库中没有消息、通知或站内信相关的模型、服务或接口。
