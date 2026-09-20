from __future__ import annotations

import os
import socket
import time

import pytest

os.environ.setdefault("USE_MOCK_DATA", "1")


def _port_open(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.25)
        return sock.connect_ex((host, port)) == 0


@pytest.fixture(scope="session")
def app_url():
    preset = os.environ.get("BASE_URL")
    if preset:
        yield preset.rstrip("/")
        return

    os.environ["USE_MOCK_DATA"] = "1"
    os.environ.setdefault("GRADIO_SERVER_NAME", "127.0.0.1")
    from app import demo, launch_app

    host = os.environ["GRADIO_SERVER_NAME"]
    preferred = int(os.environ.get("GRADIO_SERVER_PORT", "7860"))
    port = next((candidate for candidate in range(preferred, preferred + 20) if not _port_open(host, candidate)), None)
    if port is None:
        raise RuntimeError("No free port available for the Gradio app")
    os.environ["GRADIO_SERVER_PORT"] = str(port)
    launch_app(prevent_thread_lock=True, server_name=host, server_port=port)

    deadline = time.time() + 45
    while time.time() < deadline and not _port_open(host, port):
        time.sleep(0.25)
    if not _port_open(host, port):
        demo.close()
        raise RuntimeError("Gradio app did not start on port %s" % port)

    yield f"http://{host}:{port}"
    demo.close()
