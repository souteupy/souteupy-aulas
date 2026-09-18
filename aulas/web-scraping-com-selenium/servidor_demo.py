from __future__ import annotations

import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

SITE = Path(__file__).with_name("site")


def criar_servidor(host: str, porta: int) -> ThreadingHTTPServer:
    handler = partial(SimpleHTTPRequestHandler, directory=SITE)
    return ThreadingHTTPServer((host, porta), handler)


def main() -> None:
    parser = argparse.ArgumentParser(description="Servidor da página dinâmica de demo.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--porta", type=int, default=8000)
    args = parser.parse_args()

    servidor = criar_servidor(args.host, args.porta)
    url = f"http://{args.host}:{servidor.server_port}/"
    print(f"Página de demonstração em {url}")
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        print("\nServidor encerrado.")
    finally:
        servidor.server_close()


if __name__ == "__main__":
    main()
