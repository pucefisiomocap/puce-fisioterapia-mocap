"""CLI para servir PUCE MoCap Web."""

from __future__ import annotations

import argparse

import uvicorn

from puce_mocap.web.app import create_app


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Servidor web de PUCE MoCap Fisioterapia.")
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host de escucha. En un VPS se recomienda 127.0.0.1 detrás de un proxy HTTPS.",
    )
    parser.add_argument("--port", default=8000, type=int, help="Puerto HTTP interno.")
    args = parser.parse_args(argv)
    if args.host not in {"127.0.0.1", "localhost"}:
        print("Advertencia: use HTTPS y autenticación mediante un proxy antes de exponer este servicio.")
    uvicorn.run(create_app(), host=args.host, port=args.port, log_level="info")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
