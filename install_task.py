"""安装/卸载「ECJTU校园网自动登录」Windows 任务计划。

自动适配本机环境: pythonw 路径、用户名、脚本目录均为运行时探测,
整个文件夹拷到任何装了 Python 的 Windows 电脑上都能直接安装。

用法:
  python install_task.py            安装（创建任务计划）
  python install_task.py --remove   卸载（删除任务计划）
  python install_task.py --query    查看任务状态
"""
import getpass
import subprocess
import sys
from pathlib import Path

TASK_NAME = "ECJTU校园网自动登录"
HERE = Path(__file__).resolve().parent
XML = HERE / "task.xml"

# 触发事件: 网络连接成功 (Microsoft-Windows-NetworkProfile/Operational, EventID 10000)
# 已做 XML 实体转义, 直接嵌入 Subscription 节点
SUBSCRIPTION = (
    '&lt;QueryList&gt;&lt;Query Id="0" Path="Microsoft-Windows-NetworkProfile/Operational"&gt;'
    '&lt;Select Path="Microsoft-Windows-NetworkProfile/Operational"&gt;'
    "*[System[(EventID=10000)]]&lt;/Select&gt;&lt;/Query&gt;&lt;/QueryList&gt;"
)

TEMPLATE = """<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.4" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo>
    <Description>连上网时自动登录华东交通大学校园网门户 (autologin.py)</Description>
  </RegistrationInfo>
  <Triggers>
    <EventTrigger>
      <Enabled>true</Enabled>
      <Subscription>{subscription}</Subscription>
    </EventTrigger>
  </Triggers>
  <Principals>
    <Principal id="Author">
      <UserId>{user}</UserId>
      <LogonType>InteractiveToken</LogonType>
      <RunLevel>LeastPrivilege</RunLevel>
    </Principal>
  </Principals>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <Enabled>true</Enabled>
    <Hidden>false</Hidden>
    <ExecutionTimeLimit>PT5M</ExecutionTimeLimit>
    <StartWhenAvailable>true</StartWhenAvailable>
  </Settings>
  <Actions Context="Author">
    <Exec>
      <Command>{pythonw}</Command>
      <Arguments>"{script}"</Arguments>
      <WorkingDirectory>{workdir}</WorkingDirectory>
    </Exec>
  </Actions>
</Task>
"""


def schtasks(*args):
    r = subprocess.run(["schtasks", *args], capture_output=True,
                       encoding="gbk", errors="replace")
    out = (r.stdout + r.stderr).strip()
    if out:
        print(out)
    return r.returncode


def pythonw():
    """pythonw.exe 与当前解释器同目录; 用它运行脚本才不会弹黑色控制台窗口"""
    p = Path(sys.executable).with_name("pythonw.exe")
    if not p.exists():
        sys.exit(f"错误: 未找到 pythonw.exe ({p})，请重新安装 Python 并勾选 Add to PATH")
    return p


def install():
    xml = TEMPLATE.format(subscription=SUBSCRIPTION, user=getpass.getuser(),
                          pythonw=pythonw(), script=HERE / "autologin.py",
                          workdir=HERE)
    XML.write_bytes(xml.encode("utf-16"))  # schtasks 只接受 UTF-16 编码的 XML
    print(f"已生成 {XML.name}（已适配本机 Python 路径与用户名）")
    return schtasks("/create", "/tn", TASK_NAME, "/xml", str(XML), "/f")


def main():
    if "--remove" in sys.argv:
        return schtasks("/delete", "/tn", TASK_NAME, "/f")
    if "--query" in sys.argv:
        return schtasks("/query", "/tn", TASK_NAME, "/v", "/fo", "list")
    return install()


if __name__ == "__main__":
    sys.exit(main())
