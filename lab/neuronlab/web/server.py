"""`lab serve`: Ergo, the pages of the lab, on http://127.0.0.1:8765 (standard library only).

GET  /                         the single page (static/index.html, ES modules, no build step)
GET  /api/...                  view models (api.py, legacy.py), JSON
GET  /api/jobs/<id>/events     server-sent events of a job: steps, progress, log lines, end
POST /api/...                  actions: start or cancel a job, replay a row, check or save a task definition

The server listens on 127.0.0.1 only. A POST must carry the header `X-Ergo: 1` and a JSON body: a page of another
site cannot send that without a CORS preflight, which this server never answers, and the Host header must name
this machine (no DNS rebinding).
"""
import json
import mimetypes
import os
import pathlib
import re
import socket
import threading
import time
import traceback
import urllib.parse
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .. import dsl, paths, taskdef
from . import api, history, legacy, runner as runner_module

STATIC = pathlib.Path(__file__).parent / "static"
MAX_BODY = 512 * 1024 * 1024  # uploads of legacy CSV files come as base64 JSON
LOCAL_HOSTS = ("127.0.0.1", "localhost", "[::1]")


class Routes:
    """Path patterns -> handlers; a handler gets the match groups, the query and the body."""

    def __init__(self):
        self.get, self.post = [], []

    def add(self, method, pattern, handler):
        getattr(self, method).append((re.compile(f"^{pattern}$"), handler))

    def find(self, method, path):
        for pattern, handler in getattr(self, method):
            m = pattern.match(path)
            if m:
                return handler, m.groups()
        return None, None


def first(query, name, default=None):
    return query.get(name, [default])[0]


def build_routes(runner):
    r = Routes()
    r.add("get", "/api/runs", lambda q, b: api.runs_view(runner))
    r.add("get", r"/api/runs/([^/]+)", lambda q, b, run: api.run_detail(run, first(q, "value")))
    r.add("get", r"/api/runs/([^/]+)/clusters", lambda q, b, run: api.clusters_view(run, first(q, "value")))
    r.add("get", r"/api/runs/([^/]+)/trees",
          lambda q, b, run: api.trees_view(run, first(q, "value"), first(q, "set", 0)))
    r.add("get", r"/api/runs/([^/]+)/flow",
          lambda q, b, run: api.flow_view(run, first(q, "value"), first(q, "candidate")))
    r.add("get", r"/api/jobs/([^/]+)", lambda q, b, job: api.job_view(job, runner))
    r.add("get", "/api/tasks", lambda q, b: api.tasks_view())
    r.add("get", r"/api/tasks/([^/]+)", lambda q, b, task: api.task_definition(task))
    r.add("get", "/api/legacy", lambda q, b: legacy.overview())
    r.add("get", r"/api/legacy/tables/([^/]+)", lambda q, b, name: legacy.table(name))
    r.add("get", "/api/settings", lambda q, b: api.settings())
    r.add("post", "/api/jobs", lambda q, b: runner.submit(b["action"], b["task"], b.get("options") or {}))
    r.add("post", r"/api/jobs/([^/]+)/cancel", lambda q, b, job: {"cancelled": runner.cancel(job)})
    r.add("post", "/api/queue/stop", lambda q, b: {"cancelled": runner.stop_queue()})
    r.add("post", "/api/flow/eval", lambda q, b: api.flow_eval(b["run"], b.get("value"), b.get("candidate"),
                                                               b.get("key"), b.get("inputs")))
    r.add("post", "/api/tasks/check", lambda q, b: {"checks": taskdef.check(b["definition"])})
    r.add("post", "/api/tasks/save", lambda q, b: {"path": str(taskdef.save(b["definition"]))})
    r.add("post", "/api/dsl/check", lambda q, b: api.dsl_check(b.get("task"), b["expr"]))
    r.add("post", "/api/diagram", lambda q, b: legacy.diagram(b["tables"], b["joins"], b.get("highlight"),
                                                               b.get("extra")))
    r.add("post", "/api/legacy/folder", lambda q, b: legacy.switch(b["path"]))
    r.add("post", "/api/legacy/upload", lambda q, b: api.upload(b["files"]))
    r.add("post", "/api/targets/preview", lambda q, b: api.target_preview(b["definition"]))
    r.add("post", "/api/pairs/resolve", lambda q, b: api.pair_resolve(b["definition"], b["key"]))
    return r


class Handler(BaseHTTPRequestHandler):
    server_version = "Ergo/1"
    routes = None
    runner = None

    def log_message(self, fmt, *args):  # quiet: the page polls
        pass

    def host_ok(self):
        host = (self.headers.get("Host") or "").rsplit(":", 1)[0]
        return host in LOCAL_HOSTS

    def send_json(self, data, status=HTTPStatus.OK):
        body = json.dumps(data, default=str).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def send_file(self, path, content_type=None):
        data = path.read_bytes()
        self.send_response(HTTPStatus.OK)
        kind = content_type or mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        if kind.startswith("text/") or kind in ("application/javascript", "application/json"):
            kind += "; charset=utf-8"
        self.send_header("Content-Type", kind)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if not self.host_ok():
            return self.send_error(HTTPStatus.FORBIDDEN, "unknown host")
        url = urllib.parse.urlsplit(self.path)
        path, query = urllib.parse.unquote(url.path), urllib.parse.parse_qs(url.query)
        if path in ("/", "/index.html"):
            return self.send_file(STATIC / "index.html", "text/html")
        if path.startswith("/static/"):
            target = (STATIC / path[len("/static/"):]).resolve()
            if STATIC.resolve() not in target.parents or not target.is_file():
                return self.send_error(HTTPStatus.NOT_FOUND)
            kind = "application/javascript" if target.suffix == ".js" else None
            return self.send_file(target, kind)
        if path == "/atlas":
            atlas = paths.RUNS / "atlas.html"
            return self.send_file(atlas, "text/html") if atlas.exists() else self.send_error(
                HTTPStatus.NOT_FOUND, "no atlas yet: run `lab viz`")
        m = re.match(r"^/files/([^/]+)/([^/]+)$", path)
        if m:
            target = api.artifact_path(m.group(1), m.group(2))
            if target is None:
                return self.send_error(HTTPStatus.NOT_FOUND)
            return self.send_file(target, "text/plain" if target.suffix in (".md", ".jsonl") else None)
        m = re.match(r"^/api/jobs/([^/]+)/events$", path)
        if m:
            return self.stream(m.group(1))
        handler, groups = self.routes.find("get", path)
        if handler is None:
            return self.send_error(HTTPStatus.NOT_FOUND)
        self.answer(handler, query, None, groups)

    def do_POST(self):
        if not self.host_ok() or self.headers.get("X-Ergo") != "1":
            return self.send_error(HTTPStatus.FORBIDDEN, "missing X-Ergo header")
        length = int(self.headers.get("Content-Length") or 0)
        if length > MAX_BODY:
            return self.send_error(HTTPStatus.REQUEST_ENTITY_TOO_LARGE)
        try:
            body = json.loads(self.rfile.read(length) or b"{}")
        except json.JSONDecodeError:
            return self.send_json({"error": "the body is not JSON"}, HTTPStatus.BAD_REQUEST)
        handler, groups = self.routes.find("post", urllib.parse.urlsplit(self.path).path)
        if handler is None:
            return self.send_error(HTTPStatus.NOT_FOUND)
        self.answer(handler, {}, body, groups)

    def answer(self, handler, query, body, groups):
        try:
            self.send_json(handler(query, body, *groups))
        except (ValueError, KeyError, dsl.Invalid, taskdef.Invalid, RuntimeError) as e:
            self.send_json({"error": str(e) or type(e).__name__}, HTTPStatus.BAD_REQUEST)
        except FileNotFoundError as e:
            self.send_json({"error": f"missing file: {e.filename}"}, HTTPStatus.NOT_FOUND)
        except Exception as e:  # noqa: BLE001 - the page shows the error, the server keeps serving
            traceback.print_exc()
            self.send_json({"error": f"{type(e).__name__}: {e}"}, HTTPStatus.INTERNAL_SERVER_ERROR)

    def stream(self, job_id):
        """Server-sent events of a job until it ends: its event lines, then its log lines, then `end`."""
        job = history.recorded().get(job_id)
        if job is None:
            return self.send_error(HTTPStatus.NOT_FOUND)
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        offsets = {"events": 0, "log": 0}
        try:
            while True:
                job = history.recorded().get(job_id, job)
                sent = False
                for name in ("events", "log"):
                    path = pathlib.Path(job[name])
                    if path.exists() and path.stat().st_size > offsets[name]:
                        with open(path, "rb") as f:
                            f.seek(offsets[name])
                            chunk = f.read()
                        complete = chunk[:chunk.rfind(b"\n") + 1]
                        offsets[name] += len(complete)
                        for line in complete.decode("utf-8", errors="replace").splitlines():
                            payload = line if name == "events" else json.dumps({"event": "log", "text": line})
                            self.wfile.write(f"event: {name}\ndata: {payload}\n\n".encode("utf-8"))
                            sent = True
                if job["status"] not in ("queued", "running"):
                    self.wfile.write(f"event: end\ndata: {json.dumps({'status': job['status']})}\n\n".encode())
                    self.wfile.flush()
                    return
                if not sent:
                    self.wfile.write(b": keep-alive\n\n")
                self.wfile.flush()
                time.sleep(0.5)
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            return


class Server(ThreadingHTTPServer):
    """One server per port: on Windows SO_REUSEADDR would let a second `lab serve` share the port silently."""
    daemon_threads = True
    allow_reuse_address = os.name != "nt"

    def server_bind(self):
        if os.name == "nt":
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        super().server_bind()


def serve(port=8765):
    runner = runner_module.Runner()
    Handler.routes = build_routes(runner)
    Handler.runner = runner
    httpd = Server(("127.0.0.1", port), Handler)
    print(f"Ergo on http://127.0.0.1:{port}  (legacy {paths.LEGACY}, targets {paths.TARGETS})", flush=True)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()


def start_in_thread(port=0):
    """A server on a free port in a background thread (tests): returns (server, runner, base url)."""
    runner = runner_module.Runner()
    Handler.routes = build_routes(runner)
    httpd = Server(("127.0.0.1", port), Handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd, runner, f"http://127.0.0.1:{httpd.server_address[1]}"


