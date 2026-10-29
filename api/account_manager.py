import configparser
import glob
import json
import os
import threading
import time
from typing import Optional


def extract_uid_from_data(data: dict) -> str:
    uid = str(data.get("uid") or "").strip()
    if uid and uid.isdigit():
        return uid
    cookies = str(data.get("cookies") or "")
    for item in cookies.split(";"):
        if "=" in item:
            k, v = item.strip().split("=", 1)
            if k in ("_uid", "UID") and v.strip() and v.strip().isdigit():
                return v.strip()
    return ""


class AccountManager:
    """管理独立账号配置文件的存储与切换."""

    _lock = threading.Lock()

    def __init__(self, accounts_dir: str = "accounts", auto_import_legacy: bool = True) -> None:
        self.accounts_dir = accounts_dir
        os.makedirs(self.accounts_dir, exist_ok=True)
        self._active_account_id: Optional[str] = None
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        default_dir = os.path.join(base_dir, "accounts")
        if auto_import_legacy and os.path.abspath(self.accounts_dir) == os.path.abspath(default_dir):
            self._import_legacy_if_needed()

    def _import_legacy_if_needed(self) -> None:
        """账号目录为空时从项目根目录迁移已有配置与Cookie."""
        ini_files = glob.glob(os.path.join(self.accounts_dir, "*.ini"))
        if ini_files:
            return

        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        cfg_file = os.path.join(base_dir, "config.ini")
        cookies_file = os.path.join(base_dir, "cookies.txt")

        legacy_data = {}
        username = "default"

        if os.path.exists(cfg_file):
            cfg = configparser.ConfigParser(interpolation=None)
            try:
                cfg.read(cfg_file, encoding="utf8")
                if cfg.has_section("common"):
                    legacy_data = dict(cfg.items("common"))
                    username = legacy_data.get("username", "default")
            except Exception:
                pass

        if os.path.exists(cookies_file):
            try:
                with open(cookies_file, "r", encoding="utf8") as f:
                    c_txt = f.read().strip()
                if c_txt:
                    legacy_data["cookies"] = c_txt
                    legacy_data["use_cookies"] = "true"
            except Exception:
                pass

        if legacy_data:
            self.save_account(username, legacy_data)

    def list_accounts(self) -> list[dict]:
        ini_files = glob.glob(os.path.join(self.accounts_dir, "*.ini"))
        results = []
        for file_path in ini_files:
            file_name = os.path.basename(file_path)
            acc_id = os.path.splitext(file_name)[0]
            config = configparser.ConfigParser(interpolation=None)
            try:
                config.read(file_path, encoding="utf8")
            except configparser.Error as e:
                from api.logger import logger
                logger.error(f"配置文件解析失败 {file_path}: {e}")
                raise

            common_dict = dict(config.items("common")) if config.has_section("common") else {}
            uid = extract_uid_from_data(common_dict)

            # 统一迁移历史手机号文件至超星唯一UID命名
            if uid and acc_id != uid:
                new_path = os.path.join(self.accounts_dir, f"{uid}.ini")
                if not os.path.exists(new_path):
                    try:
                        os.replace(file_path, new_path)
                        file_path = new_path
                        file_name = f"{uid}.ini"
                        acc_id = uid
                    except OSError:
                        pass

            username = config.get("common", "username", fallback=acc_id)
            results.append({
                "id": acc_id,
                "uid": uid or acc_id,
                "username": username,
                "file": file_name,
                "path": file_path,
                "active": (acc_id == self._active_account_id),
            })

        if results and self._active_account_id is None:
            self._active_account_id = results[0]["id"]
            results[0]["active"] = True

        return results

    def get_active_account(self) -> Optional[dict]:
        accounts = self.list_accounts()
        if not accounts:
            return None
        for acc in accounts:
            if acc["id"] == self._active_account_id:
                cfg = configparser.ConfigParser(interpolation=None)
                cfg.read(acc["path"], encoding="utf8")
                res = dict(acc)
                if cfg.has_section("common"):
                    res.update(dict(cfg.items("common")))
                return res
        return None

    def switch_account(self, account_id: str) -> Optional[dict]:
        self._active_account_id = account_id
        return self.get_active_account()

    def delete_account(self, account_id: str) -> bool:
        """删除指定账号的配置文件."""
        safe_name = "".join(c for c in account_id if c.isalnum() or c in ("_", "-"))
        if not safe_name:
            return False
        file_path = os.path.join(self.accounts_dir, f"{safe_name}.ini")
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except OSError:
                return False
            if self._active_account_id == safe_name:
                self._active_account_id = None
                remaining = self.list_accounts()
                if remaining:
                    self._active_account_id = remaining[0]["id"]
            return True
        return False

    def save_account(self, username: str, data: dict) -> str:
        # 提取超星原生UID作为文件名以合并扫码与账号登录配置
        uid = extract_uid_from_data(data)
        if not uid and str(username).strip().isdigit() and len(str(username).strip()) < 11:
            uid = str(username).strip()

        account_id = uid or username
        safe_name = "".join(c for c in account_id if c.isalnum() or c in ("_", "-")) or "default"
        file_path = os.path.join(self.accounts_dir, f"{safe_name}.ini")

        config = configparser.ConfigParser(interpolation=None)
        if os.path.exists(file_path):
            config.read(file_path, encoding="utf8")

        if not config.has_section("common"):
            config.add_section("common")

        if uid:
            config.set("common", "uid", uid)
        if "username" in data and str(data["username"]).strip():
            config.set("common", "username", str(data["username"]).strip())
        elif not config.has_option("common", "username"):
            config.set("common", "username", username)

        for key, value in data.items():
            if value is not None and key != "username":
                config.set("common", str(key), str(value))

        with open(file_path, "w", encoding="utf8") as f:
            config.write(f)

        self._active_account_id = safe_name
        return file_path

    def get_daily_watched_seconds(self, username: str) -> float:
        """获取指定账号今日已观看视频的累计时长(秒)."""
        today_str = time.strftime("%Y-%m-%d")
        safe_name = "".join(c for c in username if c.isalnum() or c in ("_", "-")) or "default"
        stats_file = os.path.join(self.accounts_dir, "daily_watch.json")
        try:
            if os.path.exists(stats_file):
                with open(stats_file, "r", encoding="utf8") as f:
                    data = json.load(f)
                return float(data.get(f"{safe_name}_{today_str}", 0.0))
        except Exception:
            pass
        return 0.0

    def add_daily_watched_seconds(self, username: str, seconds: float) -> float:
        """累加指定账号今日观看视频时长(秒)并持久化."""
        today_str = time.strftime("%Y-%m-%d")
        safe_name = "".join(c for c in username if c.isalnum() or c in ("_", "-")) or "default"
        key = f"{safe_name}_{today_str}"
        stats_file = os.path.join(self.accounts_dir, "daily_watch.json")
        with self._lock:
            data = {}
            try:
                if os.path.exists(stats_file):
                    with open(stats_file, "r", encoding="utf8") as f:
                        data = json.load(f)
            except Exception:
                data = {}
            new_val = round(float(data.get(key, 0.0)) + float(seconds), 2)
            data[key] = new_val
            try:
                temp_file = f"{stats_file}.tmp"
                with open(temp_file, "w", encoding="utf8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                os.replace(temp_file, stats_file)
            except Exception:
                pass
            return new_val
