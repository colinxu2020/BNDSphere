## 快速开始

### 后端

python 3.14+, uv 0.10.11+

``` bash
cd backend
uv sync
uv run alembic upgrade head
uv run uvicorn main:app
```
