import time
import requests
from typing import Optional
from api.cipher import AESCipher
from api.config import GlobalConst as gc


class ChaoXingQRManager:
    """超星扫码认证与账号密码登录管理服务."""

    def __init__(self) -> None:
        self._sessions: dict[str, dict] = {}
        self.cipher = AESCipher()

    def create_session(self) -> dict:
        session = requests.Session()
        session.headers.update(gc.HEADERS)
        url = "https://passport2.chaoxing.com/createqr?type=1&shortUrl=1"
        try:
            resp = session.get(url, timeout=5)
            data = resp.json()
            if data.get("status"):
                uuid = data["uuid"]
                enc = data["enc"]
                qr_url = f"https://passport2.chaoxing.com/qr/showCode?uuid={uuid}"
                self._sessions[uuid] = {
                    "uuid": uuid,
                    "enc": enc,
                    "session": session,
                    "created_at": time.time(),
                }
                return {
                    "status": True,
                    "session_id": uuid,
                    "qr_url": qr_url,
                }
            return {"status": False, "msg": "获取二维码失败"}
        except Exception as e:
            return {"status": False, "msg": str(e)}

    def check_status(self, session_id: str) -> dict:
        sess_data = self._sessions.get(session_id)
        if not sess_data:
            return {"status": "EXPIRED"}

        if time.time() - sess_data["created_at"] > 300:
            self._sessions.pop(session_id, None)
            return {"status": "EXPIRED"}

        session = sess_data["session"]
        url = "https://passport2.chaoxing.com/getauthstatus"
        payload = {
            "uuid": sess_data["uuid"],
            "enc": sess_data["enc"],
        }
        try:
            resp = session.post(url, data=payload, headers=gc.HEADERS, timeout=5)
            data = resp.json()
            status_type = data.get("type")
            if status_type == 4:
                cookies_dict = {}
                for k, v in session.cookies.items():
                    cookies_dict[k] = v
                for k, v in resp.cookies.items():
                    cookies_dict[k] = v
                cookie_str = "; ".join(f"{k}={v}" for k, v in cookies_dict.items())
                uid = cookies_dict.get("_uid") or cookies_dict.get("UID") or session_id
                self._sessions.pop(session_id, None)
                return {
                    "status": "SUCCESS",
                    "cookies": cookie_str,
                    "uid": str(uid),
                }
            elif status_type == 2:
                return {"status": "CONFIRMED"}
            elif status_type in (1, 0, None):
                return {"status": "PENDING"}
            elif status_type == 6:
                self._sessions.pop(session_id, None)
                return {"status": "EXPIRED"}
            else:
                return {"status": "PENDING"}
        except Exception:
            return {"status": "PENDING"}

    def login_with_password(self, username: str, password: str) -> dict:
        session = requests.Session()
        session.headers.update(gc.HEADERS)
        url = "https://passport2.chaoxing.com/fanyalogin"
        data = {
            "fid": "-1",
            "uname": self.cipher.encrypt(username),
            "password": self.cipher.encrypt(password),
            "refer": "https%3A%2F%2Fi.chaoxing.com",
            "t": True,
            "forbidotherlogin": 0,
            "validate": "",
            "doubleFactorLogin": 0,
            "independentId": 0,
        }
        try:
            resp = session.post(url, headers=gc.HEADERS, data=data, timeout=5)
            res_json = resp.json()
            if res_json.get("status") is True:
                cookie_str = "; ".join(f"{k}={v}" for k, v in session.cookies.items())
                uid = session.cookies.get("_uid") or session.cookies.get("UID") or username
                return {
                    "status": "SUCCESS",
                    "cookies": cookie_str,
                    "uid": str(uid),
                }
            return {
                "status": "FAILED",
                "msg": str(res_json.get("msg2", "认证失败")),
            }
        except Exception as e:
            return {"status": "FAILED", "msg": str(e)}
