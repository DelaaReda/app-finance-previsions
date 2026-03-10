#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
from contextlib import suppress


async def _pipe(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
    try:
        while True:
            chunk = await reader.read(65536)
            if not chunk:
                break
            writer.write(chunk)
            await writer.drain()
    finally:
        with suppress(Exception):
            writer.close()
            await writer.wait_closed()


async def _handle(
    client_reader: asyncio.StreamReader,
    client_writer: asyncio.StreamWriter,
    *,
    target_host: str,
    target_port: int,
) -> None:
    try:
        upstream_reader, upstream_writer = await asyncio.open_connection(target_host, target_port)
    except Exception:
        with suppress(Exception):
            client_writer.close()
            await client_writer.wait_closed()
        return

    await asyncio.gather(
        _pipe(client_reader, upstream_writer),
        _pipe(upstream_reader, client_writer),
        return_exceptions=True,
    )


async def _serve(listen_host: str, listen_port: int, target_host: str, target_port: int) -> None:
    server = await asyncio.start_server(
        lambda r, w: _handle(r, w, target_host=target_host, target_port=target_port),
        host=listen_host,
        port=listen_port,
    )
    addrs = ", ".join(str(sock.getsockname()) for sock in (server.sockets or []))
    print(f"monitor-lan-proxy listening on {addrs} -> {target_host}:{target_port}", flush=True)
    async with server:
        await server.serve_forever()


def main() -> None:
    parser = argparse.ArgumentParser(description="Expose the monitor on a LAN-facing TCP socket.")
    parser.add_argument("--listen-host", default="192.168.64.9")
    parser.add_argument("--listen-port", type=int, default=7780)
    parser.add_argument("--target-host", default="127.0.0.1")
    parser.add_argument("--target-port", type=int, default=7779)
    args = parser.parse_args()
    asyncio.run(_serve(args.listen_host, args.listen_port, args.target_host, args.target_port))


if __name__ == "__main__":
    main()
