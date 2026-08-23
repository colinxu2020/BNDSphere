# BNDSphere 文档

BNDSphere 是 BNDS 社团管理平台的后端与前端一体化仓库。本文档目录是项目文档的统一入口。

## 文档导航

### 架构文档

- [系统总览](architecture/overview.md) — 功能子域划分、角色与权限矩阵
- [数据库架构](architecture/database.md) — 数据表、枚举、实体关系图（与 Alembic 迁移同步）
- [API 参考](architecture/API.md) — 全部 `/api/v1` 端点清单

### 指南

- [快速开始](getting-started.md) — 环境搭建、开发、测试流程

### 业务流程

- [业务流程](business_process.md) — 各业务线的申请/审核/验证流转说明

### 功能清单

- [TODO.md](../TODO.md) — 功能实现进度清单（`[x]` 已实现 / `[ ]` 待实现）

## 项目结构速览

```
.
├── backend/               # FastAPI 后端（Python 3.14 + uv）
│   ├── app/
│   │   ├── models/        # SQLAlchemy ORM 模型（含 moderations/、verifications/ 子包）
│   │   ├── schemas/       # Pydantic 请求/响应模型
│   │   ├── services/      # 业务逻辑层
│   │   ├── repositories/  # 数据访问层
│   │   └── api/v1/        # API 路由（依赖方向：api/v1 → schemas → services → repositories → models）
│   └── migrations/        # Alembic 迁移
├── frontend/              # React/TypeScript 前端
├── infra/                 # Caddy 等基础设施配置
├── scripts/               # 辅助脚本（如 gen-secrets.sh）
└── docker-compose*.yml    # 开发/构建/测试 compose 编排
```

## 技术栈

| 层 | 技术 |
| --- | --- |
| 后端框架 | FastAPI（异步） |
| ORM | SQLAlchemy 2.x（异步） |
| 数据库 | PostgreSQL |
| 迁移 | Alembic |
| 校验/序列化 | Pydantic v2 |
| 认证 | JWT（OAuth2 Bearer） |
| 对象存储 | OSS（S3 兼容，预签名 URL 上传） |
| 依赖/构建 | uv（Python 3.14+，禁用 pip） |
| 前端 | React + TypeScript（Node 22+） |
| 测试 | pytest + pytest-asyncio |
| Lint/类型 | ruff + mypy（strict） |
