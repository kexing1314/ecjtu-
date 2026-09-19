# ECJTU 校园网自动登录

校园网（ECJTU-Stu）全自动免感知登录：连上 WiFi 的瞬间自动完成门户认证，
告别每次手动"等网页弹出 → 输学号密码 → 点登录"。

纯 Python 标准库实现，无任何第三方依赖。

## 效果

```
以前:  连 WiFi → 浏览器弹认证页 → 输学号密码 → 点登录
现在:  连 WiFi → (几秒后已自动登录, 全程无感)
```

## 安装（约 1 分钟）

1. 安装 [Python 3.8+](https://www.python.org/downloads/)，安装时**务必勾选 "Add Python to PATH"**
2. 手动连接一次 ECJTU-Stu WiFi，确保勾选了"自动连接"
3. 把本文件夹下载/克隆到电脑任意位置（路径随意，安装时自动适配）
4. 双击 **`配置账号密码.bat`**，按提示输入学号、校园网密码、运营商
5. 双击 **`管理任务.bat`** → 输 `1` 安装计划任务 → 完成

之后开机、回宿舍、断网重连……都不用管了。

## 文件说明

| 文件 | 作用 |
|---|---|
| `autologin.py` | 核心脚本：探测门户状态 → 未登录则发认证请求（约 170 行，纯标准库） |
| `install_task.py` | 任务计划安装器：自动探测本机 pythonw 路径/用户名/目录，生成并注册计划任务 |
| `配置账号密码.bat` | 首次配置学号、密码、运营商（保存到 `config.json`） |
| `立即登录.bat` | 手动触发一次"检测+登录"，用于测试或掉线后重连 |
| `管理任务.bat` | 安装 / 卸载 / 查看自动登录计划任务 |
| `autologin.log` | （运行后生成）运行日志，排障看这里，自动限制在 100KB 内 |
| `task.xml` | （安装时生成）任务计划定义，已适配本机路径 |

## 原理说明

### 1. 华东交大校园网的认证方式

ECJTU-Stu 是**开放 WiFi**（连接本身不要密码），上网权限靠 **Dr.COM eportal 门户认证**：
未登录时所有 HTTP 流量被重定向到认证网关 `172.16.2.100`，也就是你看到的那个登录网页。
"自动登录"要替代的只是这个网页表单提交，WiFi 连接本身 Windows 早就自动做了。

### 2. 登录请求（脚本做的事 = 网页点"登录"按钮做的事）

```
POST http://172.16.2.100:801/eportal/?c=ACSetting&a=Login&protocol=http:&hostname=172.16.2.100
     &iTermType=1&wlanacip=null&wlanacname=null&mac=00-00-00-00-00-00&enAdvert=0&queryACIP=0&loginMethod=1
Content-Type: application/x-www-form-urlencoded

DDDDD=,0,{学号}@{运营商}&upass={密码}&R1=0&R2=0&R3=0&R6=0&para=00&0MKKey=123456&...
```

- 运营商取值：`telecom`（电信）/ `cmcc`（移动）/ `unicom`（联通）
- 密码为明文传输（门户本身如此），脚本会对特殊字符做 URL 转义
- **结果判断**：服务器返回 302，看 `Location` 响应头——
  - 不含 `RetCode=` → 登录成功
  - `RetCode=userid error1` → 账号不存在或运营商选错
  - `RetCode=userid error2` → 密码错误
  - `RetCode=512` → AC 认证失败（可能已在别处登录）
  - `RetCode=Rad:Oppp error: Limit Users Err` → 超出设备数量限制

### 3. 状态探测（决定要不要登录）

GET `http://172.16.2.100`（3 秒超时）：

| 现象 | 判定 | 动作 |
|---|---|---|
| 连不通（超时/拒绝） | 不在校园网 | 静默退出 |
| 页面含"注销页" | 已登录 | 退出 |
| 重定向到 eportal 登录页 | 未登录 | 发登录请求（网络故障重试 3 次） |
| 以上都不是 | 该 IP 被别的设备占用 | **拒绝发送密码**，退出 |

最后一行是防呆设计：`172.16.2.100` 是内网地址，理论上别的网络里也可能有设备用它，
脚本会先确认对面真的是华东交大的门户才发密码。

### 4. 自动触发（为什么不需要常驻后台）

不轮询、不驻留进程，用 **Windows 任务计划程序的"事件触发器"**（系统原生功能）：

- 事件源：`Microsoft-Windows-NetworkProfile/Operational` 日志，**EventID 10000 = 网络连接成功**
- 每次连上任何网络，Windows 自动以 `pythonw.exe`（无窗口）运行 `autologin.py`
- 脚本按上表自我判断：不在校园网 → 3 秒内静默退出，零副作用；在校园网未登录 → 登录
- 任务设置 `IgnoreNew` 防止重复触发堆叠，`PT5M` 超时上限兜底
- 另配**登录触发器**（延迟 10 秒）：覆盖开机时 WiFi 在 Windows 登录界面前就连好、
  错过联网事件的场景——登录后 10 秒自动补一次检测

`install_task.py` 安装时会探测本机的 pythonw 路径、Windows 用户名和脚本所在目录写入
`task.xml`，所以**换电脑无需改任何文件**，重新双击安装即可。

## 常见问题

- **bat 双击闪退或乱码？** bat 为 ANSI(GBK) 编码（中文 cmd 的标准），用编辑器改过请"另存为 ANSI"；
  闪退多半是没装 Python 或没勾选 Add to PATH。
- **怎么换账号/运营商？** 再跑一次 `配置账号密码.bat`。
- **半夜被踢下线不会自动重连？** 事件触发只覆盖"重新连网"。被强制注销后双击 `立即登录.bat` 即可；
  如需定时自动重连，可自行给任务加重复触发器。
- **想彻底卸载？** `管理任务.bat` → `2`，再删掉本文件夹即可，无注册表残留。
- **安全吗？** 密码明文存在本机 `config.json`（已 gitignore）；请求只发给校内认证网关
  `172.16.2.100`，不发往任何外部地址。

## 致谢与来源

- 认证协议参考自开源项目 [XY0797/ECJTUsWLANAutoLogin](https://github.com/XY0797/ECJTUsWLANAutoLogin)（GPLv3），
  并得到 [Replica0110/ECJTU-AutoLogin-Desktop](https://github.com/Replica0110/ECJTU-AutoLogin-Desktop)、
  [AccAutomaton/ECJTU-CAN-Helper](https://github.com/AccAutomaton/ECJTU-CAN-Helper) 等项目的交叉印证
- 本项目为独立的 Python 实现，代码以 MIT 协议提供
- 仅供华东交通大学师生个人学习使用；若学校升级认证系统导致失效，提 issue 或自行抓包更新 `LOGIN_URL`
