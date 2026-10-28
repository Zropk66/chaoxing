import configparser
import glob
import os
from typing import Optional


class AccountManager:
    """管理独立账号配置文件的存储与切换."""

    def __init__(self, accounts_dir: str = "accounts") -> None:
        self.accounts_dir = accounts_dir
        os.makedirs(self.accounts_dir, exist_ok=True)
        self._active_account_id: Optional[str] = None

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

            username = config.get("common", "username", fallback=acc_id)
            results.append({
                "id": acc_id,
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

    def save_account(self, username: str, data: dict) -> str:
        safe_name = "".join(c for c in username if c.isalnum() or c in ("_", "-")) or "default"
        file_path = os.path.join(self.accounts_dir, f"{safe_name}.ini")

        config = configparser.ConfigParser(interpolation=None)
        if os.path.exists(file_path):
            config.read(file_path, encoding="utf8")

        if not config.has_section("common"):
            config.add_section("common")

        config.set("common", "username", username)
        for key, value in data.items():
            config.set("common", str(key), str(value))

        with open(file_path, "w", encoding="utf8") as f:
            config.write(f)

        self._active_account_id = safe_name
        return file_path
