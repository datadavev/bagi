import mimetypes
import pathlib

import fastapi
import fastapi.responses
import fastapi.templating

TEMPLATES_PATH = pathlib.Path(__file__).parent / "templates"
CHUNK_SIZE = 1024 * 1024


def create_app(pid: str, fs) -> fastapi.FastAPI:
    app = fastapi.FastAPI()
    templates = fastapi.templating.Jinja2Templates(directory=TEMPLATES_PATH)
    app.state.config = {
        pid: {
            "fs": fs,
        },
        "templates": templates,
    }

    @app.get("/base/{pid}")
    async def read_manifest(request: fastapi.Request, pid):
        if pid not in request.app.state.config:
            raise fastapi.HTTPException(
                status_code=fastapi.status.HTTP_404_NOT_FOUND,
                detail=f"Not found: {pid}",
            )
        context = {"request": request, "pid": pid, "manifest": "index.parquet"}
        return app.state.config["templates"].TemplateResponse(
            request, name="index.html", context=context
        )

    @app.head("/base/{pid}/{item_path:path}")
    @app.get("/base/{pid}/{item_path:path}")
    async def read_item(
        request: fastapi.Request,
        pid: str,
        item_path: str,
        range: str | None = fastapi.Header(None),
    ):
        try:
            fs = request.app.state.config[pid]["fs"]
        except KeyError as err:
            raise fastapi.HTTPException(
                status_code=fastapi.status.HTTP_404_NOT_FOUND,
                detail=f"Not found {item_path}",
            ) from err
        if not fs.exists(item_path):
            raise fastapi.HTTPException(
                status_code=fastapi.status.HTTP_404_NOT_FOUND,
                detail=f"Not found {item_path}",
            )
        file_info = fs.info(item_path)
        media_type, _ = mimetypes.guess_type(item_path)

        def iterfile(path: str, start: int, end: int):
            with fs.open(path, "rb") as f:
                f.seek(start)
                remaining = end - start + 1
                while remaining > 0:
                    current_chunk_size = min(CHUNK_SIZE, remaining)
                    data = f.read(current_chunk_size)
                    if not data:
                        break
                    remaining -= len(data)
                    yield data

        # no range, stream the file
        if range is None:
            return fastapi.responses.StreamingResponse(
                iterfile(item_path, 0, file_info["size"] - 1),
                media_type=media_type,
            )
        # Parse the Range header (e.g., "bytes=0-1048575")
        try:
            range_type, range_val = range.strip().split("=")
            if range_type != "bytes":
                raise fastapi.HTTPException(
                    status_code=400, detail="Invalid range type"
                )
            start_str, end_str = range_val.split("-")
            start = int(start_str) if start_str else 0
            end = int(end_str) if end_str else file_info["size"] - 1

            if start >= file_info["size"] or end >= file_info["size"] or start > end:
                raise fastapi.HTTPException(
                    status_code=416,
                    detail="Requested range not satisfiable",
                    headers={"Content-Range": f"bytes */{file_info['size']}"},
                )
            content_length = (end - start) + 1
            headers = {
                "Content-Range": f"bytes {start}-{end}/{file_info['size']}",
                "Accept-Ranges": "bytes",
                "Content-Length": str(content_length),
            }
            return fastapi.responses.StreamingResponse(
                iterfile(item_path, start, end),
                status_code=206,
                headers=headers,
                media_type=media_type,
            )
        except ValueError as err:
            raise fastapi.HTTPException(
                status_code=400, detail="Invalid Range header format"
            ) from err

    return app
