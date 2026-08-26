# 快速开始

BNDSphere 采用前后端分离架构，后端 FastAPI（Python 3.14 + uv），前端 React/TypeScript（Node 22+），数据库 PostgreSQL。开发/测试统一通过 Docker Compose 编排。

## 环境要求

| 组件 | 版本 | 说明 |
| --- | --- | --- |
| Python | 3.14+ | 后端运行时 |
| uv | 0.10.11+ | Python 依赖/虚拟环境管理（**禁用 pip**） |
| Node.js | 22+（Docker 内 24） | 前端 |
| Docker / Docker Desktop | 任意近期版本 | 数据库、镜像构建、测试编排 |

> WSL2 用户：需确保 Docker Desktop 已开启对应发行版的 WSL Integration（见项目已知问题）。

## 1. 生成本地密钥

compose 的 `secrets:` 块从 `secrets/` 目录读取 6 个密钥文件（数据库密码、JWT 密钥、OSS 凭证）。首次运行前生成：

```bash
./scripts/gen-secrets.sh
```

> 幂等：已存在的文件不会被覆盖（`--force` 可强制重生成）。`secrets/` 已被 gitignore，**切勿提交真实值**。

## 2. 配置环境变量

在仓库根目录创建 `.env`（compose 自动读取，非密钥类配置）：

```bash
CORS_ORIGIN=http://localhost:5173
OSS_ENDPOINT_URL=   # S3 兼容对象存储端点
OSS_BUCKET=         # 桶名
OSS_PUBLIC_BASE_URL= # 上传对象对外访问的基地址（如 CDN 域名）；与仅用于签名的 OSS_ENDPOINT_URL 区分
CADDY_PORT=80       # 可选，Caddy 对外端口
```

> OSS 凭证（`oss_access_key_id` / `oss_access_key`）走 `secrets/` 文件，不要写入 `.env`。

## 3. 启动开发环境（Docker Compose）

```bash
docker compose -f docker-compose.yml -f docker-compose.build.yml -f docker-compose.dev.yml up --build
```

> `docker-compose.build.yml` 提供 `postgres`/`backend`/`backend-dev`/`caddy` 等镜像的构建定义；首次运行（无预构建镜像）需带上它，后续增量启动可省略 `--build`。

服务一览：

| 服务 | 说明 |
| --- | --- |
| `postgres` | PostgreSQL（127.0.0.1:5432） |
| `alembic-migration` | 启动时自动 `alembic upgrade head` |
| `backend` | FastAPI 后端（dev 镜像，挂载 `./backend` 热重载） |
| `frontend` | React 前端（node:24，端口 5173） |
| `caddy` | 反向代理，对外 `CADDY_PORT`（默认 80） |

API 交互式文档：`/api/docs`（Swagger）、`/api/redoc`（ReDoc）。

## 4. 测试

验收测试通过 compose 的 `test` 服务（`--profile test`）运行，与 `make test` 等价：

```bash
make test
# 等价于：
#   ./scripts/gen-secrets.sh
#   docker compose -f docker-compose.yml -f docker-compose.build.yml build postgres backend-dev
#   docker compose -f docker-compose.yml -f docker-compose.dev.yml --profile test run test
```

测试栈：pytest + pytest-asyncio（`asyncio_mode=auto`，session-scoped event loop，见 `backend/pyproject.toml` 的 `[tool.pytest.ini_options]`）。

## 5. Lint / 类型检查

```bash
cd backend
uv run ruff check --fix app     # lint（含自动修复）
uv run ruff format app          # 格式化
uv run mypy app                 # 类型检查（strict）
```

## 6. 提交前检查

在仓库根目录安装 pre-commit / pre-push hooks：

```bash
pre-commit install --install-hooks
```

手动运行完整检查：

```bash
pre-commit run --all-files
pre-commit run --all-files --hook-stage pre-push
```

## 7. 迁移管理

新增/修改模型后生成迁移：

```bash
cd backend
uv run alembic revision --autogenerate -m "描述"
uv run alembic upgrade head
```

> 也可用 compose 的 `alembic-autorevision` 服务（`--profile autorevision`）在容器内生成迁移。迁移文件位于 `backend/migrations/versions/`，生成后务必同步 `docs/architecture/database.md`。

## 已知问题

- Docker Desktop（WSL2）文件型 secret 挂载坑：`secrets/` 源文件缺失时，Docker Desktop 会在内部 staging 建成 root 空目录，之后即使源文件恢复仍报 `not a directory` 挂载失败。修复：`docker compose down` 后 `wsl -d docker-desktop -- sh -c "umount -l <hash路径>; rm -rf <hash路径>"` 逐个清理，或直接重启 Docker Desktop。
