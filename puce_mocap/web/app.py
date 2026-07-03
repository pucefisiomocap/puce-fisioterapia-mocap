"""Aplicación FastAPI para la versión web de PUCE MoCap."""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Callable

from fastapi import Body, FastAPI, HTTPException, Request, Response
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from puce_mocap.credits import credits_payload
from puce_mocap.web.controller import PuceWebController, WebActionError


def _static_dir() -> Path:
    return Path(__file__).resolve().parent / "static"


def _assets_dir() -> Path:
    return Path(__file__).resolve().parents[1] / "resources" / "assets"


def _payload(value: dict[str, Any] | None) -> dict[str, Any]:
    return value or {}


def create_app(controller: PuceWebController | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        yield
        app.state.controller.close()

    app = FastAPI(title="PUCE MoCap Fisioterapia Web", version="1.1.0", lifespan=lifespan)
    app.state.controller = controller or PuceWebController()

    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; img-src 'self' data:; media-src 'self' blob:; "
            "connect-src 'self'; script-src 'self'; style-src 'self'; object-src 'none'; frame-ancestors 'none'"
        )
        response.headers["Permissions-Policy"] = "camera=(self), microphone=(), geolocation=()"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["X-Content-Type-Options"] = "nosniff"
        if request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store"
        return response

    app.mount("/static", StaticFiles(directory=_static_dir()), name="static")
    assets = _assets_dir()
    if assets.is_dir():
        app.mount("/assets", StaticFiles(directory=assets), name="assets")

    def ctrl() -> PuceWebController:
        return app.state.controller

    def run_action(action: Callable[[], None]) -> dict[str, Any]:
        try:
            action()
        except (WebActionError, OSError, ValueError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return {"ok": True, "state": ctrl().snapshot()}

    @app.get("/", include_in_schema=False)
    def index() -> FileResponse:
        return FileResponse(_static_dir() / "index.html")

    @app.get("/api/app-info")
    def app_info() -> dict[str, Any]:
        return ctrl().app_info()

    @app.get("/api/credits")
    def credits() -> dict[str, Any]:
        return credits_payload()

    @app.get("/api/state")
    def state() -> dict[str, Any]:
        return ctrl().snapshot()

    @app.post("/api/module")
    def set_module(payload: dict[str, Any] | None = Body(default=None)) -> dict[str, Any]:
        body = _payload(payload)
        return run_action(lambda: ctrl().set_module(str(body.get("module", ""))))

    @app.post("/api/source/camera/start")
    def camera_start(payload: dict[str, Any] | None = Body(default=None)) -> dict[str, Any]:
        return run_action(lambda: ctrl().start_camera(_payload(payload)))

    @app.post("/api/source/camera/stop")
    def camera_stop() -> dict[str, Any]:
        return run_action(ctrl().stop_camera)

    @app.post("/api/source/camera/frame")
    async def camera_frame(request: Request) -> dict[str, Any]:
        length = int(request.headers.get("content-length", "0") or 0)
        if length > 4 * 1024 * 1024:
            raise HTTPException(status_code=413, detail="El fotograma supera el límite de 4 MB.")
        try:
            visualization = ctrl().process_browser_frame(await request.body())
        except (WebActionError, OSError, ValueError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return {"ok": True, "visualization": visualization, "state": ctrl().snapshot()}

    @app.post("/api/source/freemocap/upload")
    async def freemocap_upload(request: Request, filename: str, unit: str = "sin_especificar") -> dict[str, Any]:
        try:
            destination = ctrl().allocate_freemocap_upload(filename)
            size = 0
            with destination.open("wb") as stream:
                async for chunk in request.stream():
                    size += len(chunk)
                    if size > 512 * 1024 * 1024:
                        raise WebActionError("El archivo supera el límite de 512 MB.")
                    stream.write(chunk)
            if size == 0:
                raise WebActionError("El archivo seleccionado está vacío.")
            ctrl().load_freemocap_upload(destination, unit)
        except (WebActionError, OSError, ValueError) as exc:
            if "destination" in locals():
                destination.unlink(missing_ok=True)
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return {"ok": True, "state": ctrl().snapshot()}

    @app.post("/api/source/freemocap/frame")
    def freemocap_frame(payload: dict[str, Any] | None = Body(default=None)) -> dict[str, Any]:
        return run_action(lambda: ctrl().process_freemocap_frame(_payload(payload)))

    @app.post("/api/weights/configure")
    def weights_configure(payload: dict[str, Any] | None = Body(default=None)) -> dict[str, Any]:
        return run_action(lambda: ctrl().configure_weights(_payload(payload)))

    @app.post("/api/weights/start")
    def weights_start(payload: dict[str, Any] | None = Body(default=None)) -> dict[str, Any]:
        return run_action(lambda: ctrl().start_weights(_payload(payload)))

    @app.post("/api/weights/pause")
    def weights_pause() -> dict[str, Any]:
        return run_action(ctrl().pause_weights)

    @app.post("/api/weights/reset")
    def weights_reset() -> dict[str, Any]:
        return run_action(ctrl().reset_weights)

    @app.post("/api/weights/save")
    def weights_save() -> dict[str, Any]:
        return run_action(ctrl().save_weights)

    @app.post("/api/rehab/configure")
    def rehab_configure(payload: dict[str, Any] | None = Body(default=None)) -> dict[str, Any]:
        return run_action(lambda: ctrl().configure_rehab(_payload(payload)))

    @app.post("/api/rehab/start")
    def rehab_start(payload: dict[str, Any] | None = Body(default=None)) -> dict[str, Any]:
        return run_action(lambda: ctrl().start_rehab(_payload(payload)))

    @app.post("/api/rehab/pause")
    def rehab_pause() -> dict[str, Any]:
        return run_action(ctrl().pause_rehab)

    @app.post("/api/rehab/reset")
    def rehab_reset() -> dict[str, Any]:
        return run_action(ctrl().reset_rehab)

    @app.post("/api/rehab/calibrate-wrist")
    def rehab_calibrate_wrist() -> dict[str, Any]:
        return run_action(ctrl().calibrate_wrist)

    @app.post("/api/rehab/profile/upload")
    async def rehab_profile_upload(request: Request) -> dict[str, Any]:
        content = await request.body()
        if len(content) > 1024 * 1024:
            raise HTTPException(status_code=413, detail="El perfil supera el límite de 1 MB.")
        return run_action(lambda: ctrl().load_rehab_profile_json(content))

    @app.get("/api/rehab/profile/download")
    def rehab_profile_download() -> Response:
        return Response(
            content=ctrl().rehab_profile_json(),
            media_type="application/json",
            headers={"Content-Disposition": 'attachment; filename="perfil_rehabilitacion.json"'},
        )

    @app.post("/api/rehab/save")
    def rehab_save() -> dict[str, Any]:
        return run_action(ctrl().save_rehab)

    @app.post("/api/gait/configure")
    def gait_configure(payload: dict[str, Any] | None = Body(default=None)) -> dict[str, Any]:
        return run_action(lambda: ctrl().configure_gait(_payload(payload)))

    @app.post("/api/gait/start")
    def gait_start() -> dict[str, Any]:
        return run_action(ctrl().start_gait)

    @app.post("/api/gait/stop")
    def gait_stop() -> dict[str, Any]:
        return run_action(ctrl().stop_gait)

    @app.post("/api/gait/reset")
    def gait_reset() -> dict[str, Any]:
        return run_action(ctrl().reset_gait)

    @app.get("/api/reports/latest")
    def latest_report() -> FileResponse:
        try:
            path = ctrl().latest_report()
        except WebActionError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return FileResponse(path, media_type="text/csv", filename=path.name)

    return app
