"""FastAPI 入口：提供 /api 接口，并统一代理服务 Vue 构建产物。

单进程、单端口：FastAPI 同时承担 REST 接口与前端静态资源/SPA 回退。
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse

from .config import DIST_DIR
from .routers import bills, players, recognize, settlement, stats

app = FastAPI(
    title="斗地主账单系统",
    description="斗地主对局账单管理系统 — Vue + FastAPI",
    version="3.0.0",
)

# CORS（同源下通常不需要；供开发/跨域场景使用）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---- API 路由 ----
app.include_router(players.router)
app.include_router(bills.router)
app.include_router(stats.router)
app.include_router(settlement.router)
app.include_router(recognize.router)


@app.get("/api/health", tags=["meta"])
def health():
    return {"status": "ok", "app": "doudizhu-bills", "version": app.version}


# ---- 前端静态资源 + SPA 回退（必须最后注册，作为兜底） ----
@app.get("/{path:path}", include_in_schema=False)
def spa_fallback(path: str):
    index = DIST_DIR / "index.html"
    if not index.exists():
        return JSONResponse(
            {"detail": "前端未构建，请先执行 `npm run build` 生成 dist 目录。"},
            status_code=404,
        )
    full = DIST_DIR / path
    if path and full.is_file():
        return FileResponse(full)
    return FileResponse(index)
