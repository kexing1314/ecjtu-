"""华东交通大学校园网自动登录 — Dr.COM eportal 门户认证
协议来源: 开源项目 github.com/XY0797/ECJTUsWLANAutoLogin (autoLoginECJTUAPI.java)

用法:
  python autologin.py            检测状态并自动登录 (任务计划在"连网事件"时静默调用)
  python autologin.py --setup    设置/重设 学号、密码、运营商
  python autologin.py --status   只查看当前状态
  python autologin.py --selftest 逻辑自检
"""
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

PORTAL = "http://172.16.2.100"
LOGIN_URL = (
    "http://172.16.2.100:801/eportal/?c=ACSetting&a=Login&protocol=http:"
    "&hostname=172.16.2.100&iTermType=1&wlanacip=null&wlanacname=null"
    "&mac=00-00-00-00-00-00&enAdvert=0&queryACIP=0&loginMethod=1"
)
HERE = Path(__file__).resolve().parent
CONFIG, LOG = HERE / "config.json", HERE / "autologin.log"
ISPS = {"1": "telecom", "2": "cmcc", "3": "unicom"}  # 电信 / 移动 / 联通
ERRORS = {
    "userid error1": "账号不存在，或运营商选错了",
    "userid error2": "密码错误",
    "512": "AC 认证失败（可能已在别处登录）",
    "Rad:Oppp error: Limit Users Err": "超出校园网设备数量限制",
}
FATAL = set(ERRORS) - {"512"}  # 这些错误重试也没用


def log(msg):
    line = f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {msg}"
    print(line)  # pythonw 无控制台时自动静默，不会报错
    if LOG.exists() and LOG.stat().st_size > 100_000:
        # ponytail: 日志超 100KB 只留最近 50 行，排障够用，不做轮转
        LOG.write_text("\n".join(LOG.read_text(encoding="utf-8").splitlines()[-50:]) + "\n",
                       encoding="utf-8")
    with LOG.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def _has(raw, text):
    """门户页面可能是 UTF-8 也可能是 GBK，两种编码都认一下"""
    return text.encode("utf-8") in raw or text.encode("gbk", "ignore") in raw


def status():
    """返回: 已登录 / 未登录 / 不在校园网 / 门户不认识"""
    try:
        with urllib.request.urlopen(PORTAL, timeout=3) as r:
            raw, url = r.read(65536), r.url
    except OSError:
        return "不在校园网"
    if _has(raw, "注销页"):
        return "已登录"
    if "eportal" in url or b"eportal" in raw or _has(raw, "华东交通"):
        return "未登录"
    return "门户不认识"


def build_body(user, password, isp):
    return ("DDDDD=%2C0%2C" + user + "%40" + isp
            + "&upass=" + urllib.parse.quote(password, safe="")
            + "&R1=0&R2=0&R3=0&R6=0&para=00&0MKKey=123456&buttonClicked="
            + "&redirect_url=&err_flag=&username=&password=&user=&cmd=&Login=")


def parse_location(loc):
    """Location 头没有 RetCode 即登录成功, 否则返回 (False, 错误码)"""
    if "RetCode=" not in loc:
        return True, ""
    return False, urllib.parse.unquote(loc.split("RetCode=", 1)[1].split("&", 1)[0])


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args):
        return None  # 登录结果在 302 的 Location 头里, 不能自动跟随


_OPENER = urllib.request.build_opener(_NoRedirect)


def login(cfg):
    """返回 (成功, 可重试, 消息)"""
    body = build_body(cfg["user"], cfg["password"], cfg["isp"]).encode()
    req = urllib.request.Request(
        LOGIN_URL, data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded"})
    try:
        with _OPENER.open(req, timeout=5) as r:
            return False, True, f"响应未跳转(HTTP {r.status})，视为失败"
    except urllib.error.HTTPError as e:
        loc = e.headers.get("Location") or ""
        if not loc:
            return False, True, f"HTTP {e.code} 且无 Location 头"
        ok, code = parse_location(loc)
        if ok:
            return True, False, "登录成功"
        return False, code not in FATAL, ERRORS.get(code, f"未知错误码 {code!r}")
    except OSError as e:
        return False, True, f"网络请求失败: {e}"


def setup():
    import getpass
    user = input("学号: ").strip()
    pw = getpass.getpass("校园网密码: ")
    if not user or not pw:
        sys.exit("学号和密码不能为空")
    while (choice := input("运营商 1=电信 2=移动 3=联通，输入数字: ").strip()) not in ISPS:
        print("请输入 1、2 或 3")
    CONFIG.write_text(json.dumps({"user": user, "password": pw, "isp": ISPS[choice]},
                                 ensure_ascii=False, indent=2), encoding="utf-8")
    log(f"配置已保存到 {CONFIG}（运营商: {ISPS[choice]}）")


def main():
    args = set(sys.argv[1:])
    if "--selftest" in args:
        return selftest()
    if "--setup" in args:
        setup()
        return 0

    s = status()
    if "--status" in args:
        log(f"状态: {s}")
        return 0
    if s in ("已登录", "不在校园网"):
        log(f"状态: {s}，无需登录")
        return 0
    if s == "门户不认识":
        log("172.16.2.100 返回的不是华东交大门户页面，拒绝发送密码")
        return 1
    if not CONFIG.exists():
        if sys.stdin and sys.stdin.isatty():
            setup()  # 首次交互运行: 就地配置账号密码
        else:
            log("还没有配置，请先在终端运行: python autologin.py --setup")
            return 1

    cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
    for i in range(1, 4):
        ok, retry, msg = login(cfg)
        log(f"第{i}次尝试: {msg}")
        if ok or not retry:
            return 0 if ok else 1
        time.sleep(3)
    return 1


def selftest():
    b = build_body("20231234", "p@ss&word", "cmcc")
    assert "DDDDD=%2C0%2C20231234%40cmcc" in b, b
    assert "upass=p%40ss%26word" in b, b       # 密码特殊字符必须被转义
    assert "0MKKey=123456" in b
    assert parse_location("http://172.16.2.100/eportal/index.jsp") == (True, "")
    assert parse_location("http://x/RetCode=userid error2&ac=") == (False, "userid error2")
    assert parse_location("http://x/RetCode=userid%20error2&ac=") == (False, "userid error2")
    assert parse_location("http://x/RetCode=512&a=") == (False, "512")
    assert _has("注销页".encode("gbk"), "注销页")   # GBK 页面也要能识别
    print("selftest: 全部通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
