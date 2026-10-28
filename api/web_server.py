import json
import os
import queue
from typing import Optional
from flask import Flask, Response, jsonify, render_template, request
from api.account_manager import AccountManager
from api.chaoxing_auth import ChaoXingQRManager
from api.config_manager import ConfigManager
from api.task_runner import TaskStateHub


def create_app(test_config: Optional[dict] = None) -> Flask:
    """构建本地 Web 控制台 Flask 应用服务."""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    template_dir = os.path.join(base_dir, "web", "templates")
    static_dir = os.path.join(base_dir, "web", "static")

    app = Flask(
        __name__,
        template_folder=template_dir,
        static_folder=static_dir,
        static_url_path="/static"
    )

    if test_config:
        app.config.update(test_config)

    account_mgr = AccountManager(accounts_dir=os.path.join(base_dir, "accounts"))
    auth_mgr = ChaoXingQRManager()
    hub = TaskStateHub()
    hub.set_web_mode(True)

    def get_active_config_manager() -> ConfigManager:
        active = account_mgr.get_active_account()
        if active and os.path.exists(active.get("path", "")):
            cfg_path = active["path"]
        else:
            cfg_path = os.path.join(base_dir, "config.ini")
        tmpl_path = os.path.join(base_dir, "config_template.ini")
        return ConfigManager(config_path=cfg_path, template_path=tmpl_path)

    @app.route("/")
    def index():
        if os.path.exists(os.path.join(template_dir, "index.html")):
            return render_template("index.html")
        return "Web 控制台资源准备中", 200

    @app.route("/api/accounts", methods=["GET"])
    def list_accounts():
        accounts = account_mgr.list_accounts()
        active = account_mgr.get_active_account()
        active_id = active["id"] if active else None
        return jsonify({
            "accounts": accounts,
            "active_account": active_id,
        })

    @app.route("/api/accounts/switch", methods=["POST"])
    def switch_account():
        data = request.get_json() or {}
        acc_id = data.get("account_id")
        if not acc_id:
            return jsonify({"status": "error", "msg": "缺少 account_id 参数"}), 400
        active = account_mgr.switch_account(acc_id)
        if not active:
            return jsonify({"status": "error", "msg": "账号不存在"}), 404
        return jsonify({"status": "success", "active_account": acc_id})

    @app.route("/api/auth/qr/create", methods=["POST"])
    def create_qr():
        res = auth_mgr.create_session()
        code = 200 if res.get("status") else 500
        return jsonify(res), code

    @app.route("/api/auth/qr/status/<session_id>", methods=["GET"])
    def check_qr(session_id: str):
        res = auth_mgr.check_status(session_id)
        if res.get("status") == "SUCCESS" and "cookies" in res:
            uid = res.get("uid") or session_id
            account_mgr.save_account(uid, {
                "cookies": res["cookies"],
                "use_cookies": "true",
            })
        return jsonify(res)

    @app.route("/api/auth/login", methods=["POST"])
    def password_login():
        data = request.get_json() or {}
        username = data.get("username", "").strip()
        password = data.get("password", "").strip()
        if not username or not password:
            return jsonify({"status": "error", "msg": "用户名或密码不能为空"}), 400
        res = auth_mgr.login_with_password(username, password)
        if res.get("status") == "SUCCESS":
            account_mgr.save_account(username, {
                "username": username,
                "cookies": res.get("cookies", ""),
                "use_cookies": "true",
            })
            return jsonify({"status": "success", "account_id": username})
        return jsonify({"status": "error", "msg": res.get("msg", "登录失败")}), 401

    @app.route("/api/courses", methods=["GET"])
    def get_courses():
        active = account_mgr.get_active_account()
        if not active:
            return jsonify({"courses": [], "selected_ids": []})

        cfg_mgr = get_active_config_manager()
        selected_ids = set(cfg_mgr.get_course_list())
        courses = []
        cookies_str = active.get("cookies", "")
        if cookies_str:
            try:
                from api.base import Chaoxing, Account
                from api.answer import Tiku
                account = Account(active.get("username", ""), "")
                cx = Chaoxing(account=account, tiku=Tiku())
                cookie_dict = {}
                for item in cookies_str.split(";"):
                    if "=" in item:
                        k, v = item.strip().split("=", 1)
                        cookie_dict[k] = v
                cx._session.cookies.update(cookie_dict)
                raw_courses = cx.get_course_list()
                for c in raw_courses:
                    cid = str(c.get("courseId", ""))
                    courses.append({
                        "courseId": cid,
                        "clazzId": str(c.get("clazzId", "")),
                        "cpi": str(c.get("cpi", "")),
                        "title": c.get("title", ""),
                        "teacher": c.get("teacher", ""),
                        "selected": cid in selected_ids,
                    })
            except Exception as e:
                hub.append_log("ERROR", f"获取课程列表失败: {e}")

        return jsonify({"courses": courses, "selected_ids": list(selected_ids)})

    @app.route("/api/config/course_list", methods=["POST"])
    def save_course_list():
        data = request.get_json() or {}
        course_ids = data.get("course_list", [])
        cfg_mgr = get_active_config_manager()
        cfg_mgr.set_course_list(course_ids)
        return jsonify({"status": "success"})

    @app.route("/api/config/full", methods=["GET"])
    def get_full_config():
        cfg_mgr = get_active_config_manager()
        return jsonify(cfg_mgr.get_full_config())

    @app.route("/api/config/full", methods=["POST"])
    def save_full_config():
        data = request.get_json() or {}
        cfg_mgr = get_active_config_manager()
        cfg_mgr.update_full_config(data)
        return jsonify({"status": "success"})

    @app.route("/api/speed/global", methods=["POST"])
    def set_global_speed():
        data = request.get_json() or {}
        speed = data.get("speed", 1.0)
        hub.set_global_speed(float(speed))
        return jsonify({"status": "success", "global_speed": hub.get_global_speed()})

    @app.route("/api/speed/worker", methods=["POST"])
    def set_worker_speed():
        data = request.get_json() or {}
        worker_id = data.get("worker_id")
        speed = data.get("speed", 1.0)
        if not worker_id:
            return jsonify({"status": "error", "msg": "缺少 worker_id"}), 400
        hub.set_worker_speed(worker_id, float(speed))
        return jsonify({
            "status": "success",
            "worker_id": worker_id,
            "speed": hub.get_effective_speed(worker_id),
        })

    @app.route("/api/status", methods=["GET"])
    def get_status():
        return jsonify(hub.get_snapshot())

    @app.route("/api/manual/pending", methods=["GET"])
    def get_manual_pending():
        return jsonify({"questions": hub.get_pending_questions()})

    @app.route("/api/manual/answer", methods=["POST"])
    def submit_manual_answer():
        data = request.get_json() or {}
        prompt_id = data.get("prompt_id")
        answer = data.get("answer")
        if not prompt_id:
            return jsonify({"status": "error", "msg": "缺少 prompt_id"}), 400
        ok = hub.submit_manual_answer(prompt_id, str(answer) if answer is not None else "")
        if ok:
            return jsonify({"status": "success"})
        return jsonify({"status": "not_found", "msg": "作答会话已结束或不存在"}), 404

    @app.route("/api/manual/skip", methods=["POST"])
    def skip_manual_answer():
        data = request.get_json() or {}
        prompt_id = data.get("prompt_id")
        if not prompt_id:
            return jsonify({"status": "error", "msg": "缺少 prompt_id"}), 400
        ok = hub.skip_manual_answer(prompt_id)
        if ok:
            return jsonify({"status": "success"})
        return jsonify({"status": "not_found", "msg": "作答会话已结束或不存在"}), 404

    @app.route("/api/events", methods=["GET"])
    def sse_events():
        def event_stream():
            q = hub.subscribe_events()
            try:
                snapshot = hub.get_snapshot()
                yield f"event: STATUS_UPDATE\ndata: {json.dumps(snapshot)}\n\n"
                while True:
                    try:
                        msg = q.get(timeout=25.0)
                        event_type = msg["event"]
                        data_json = json.dumps(msg["data"])
                        yield f"event: {event_type}\ndata: {data_json}\n\n"
                    except queue.Empty:
                        yield ": keep-alive\n\n"
            finally:
                hub.unsubscribe_events(q)

        return Response(event_stream(), mimetype="text/event-stream")

    return app
