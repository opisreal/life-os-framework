# .tools/ — Life OS 通知与调度基础设施

## 模块定位

`.tools/` 是 Life OS 的通知发送与定时调度层。它与具体模块（`04_career/`、`05_finance/`）解耦：通用消息发送器（`notify.sh`）对上层脚本提供统一接口，launchd plist 负责在 macOS 系统级按日历触发各模块的 reminder 脚本。任何模块只需实现自己的 `_tools/*-reminder.sh` 并调用 `notify.sh`，不需要关心底层通道细节。

---

## 文件清单

```
.tools/
├── README.md                          本文件
├── notify.sh                          通用消息发送器（lark-cli + telegram 双通道）
├── notify.config.example.json         配置模板（可提交）
├── notify.config.private.json         私有配置（已加入 .gitignore，不提交）
└── launchd/
    ├── com.lifeos.career.weekly.plist      每周一 09:00
    ├── com.lifeos.career.monthly.plist     每月  1 日 09:00
    ├── com.lifeos.career.quarterly.plist   季首  1 日 09:30（1/4/7/10 月）
    ├── com.lifeos.finance.monthly.plist    每月  3 日 09:00
    ├── com.lifeos.finance.quarterly.plist  季首  5 日 09:30（1/4/7/10 月）
    └── com.lifeos.finance.yearly.plist     1 月  8 日 09:00
```

---

## 首次安装

### 1. 配置私有参数

```bash
cp ~/life-os/.tools/notify.config.example.json \
   ~/life-os/.tools/notify.config.private.json
```

用编辑器打开 `notify.config.private.json`，填写：
- `lark.default_receive_id` — 飞书接收人/群的 open_id 或 chat_id
- `lark.receive_id_type` — 对应 `open_id` / `chat_id` / `user_id`
- 其他通道配置（telegram token/chat_id 等）

### 2. 验证 notify.sh 可用

```bash
~/life-os/.tools/notify.sh "test" "test"
```

收到消息即表示配置正确。

### 3. 安装 launchd 定时任务

```bash
cp ~/life-os/.tools/launchd/*.plist ~/Library/LaunchAgents/

for p in ~/Library/LaunchAgents/com.lifeos.*.plist; do
  launchctl load "$p"
done
```

### 4. 验证安装成功

```bash
launchctl list | grep com.lifeos
```

预期输出 6 行，每个 Label 对应一个任务（`PID` 列为 `-` 表示未在运行，属正常）。

---

## 卸载 / 暂停

```bash
# 卸载全部
for p in ~/Library/LaunchAgents/com.lifeos.*.plist; do
  launchctl unload "$p"
done
rm ~/Library/LaunchAgents/com.lifeos.*.plist

# 暂停单个（以 finance.monthly 为例）
launchctl unload ~/Library/LaunchAgents/com.lifeos.finance.monthly.plist
```

---

## 手工触发（测试用）

```bash
launchctl start com.lifeos.finance.monthly
launchctl start com.lifeos.career.weekly
# 以此类推
```

注意：手工触发要求 plist 已通过 `launchctl load` 加载，且对应的 reminder.sh 脚本存在且可执行。

---

## 任务一览

| Label | 触发时机 | 脚本 |
|---|---|---|
| com.lifeos.career.weekly | 每周一 09:00 | `04_career/_tools/weekly-reminder.sh` |
| com.lifeos.career.monthly | 每月 1 日 09:00 | `04_career/_tools/monthly-reminder.sh` |
| com.lifeos.career.quarterly | 1/4/7/10 月 1 日 09:30 | `04_career/_tools/quarterly-reminder.sh` |
| com.lifeos.finance.monthly | 每月 3 日 09:00 | `05_finance/_tools/monthly-reminder.sh` |
| com.lifeos.finance.quarterly | 1/4/7/10 月 5 日 09:30 | `05_finance/_tools/quarterly-reminder.sh` |
| com.lifeos.finance.yearly | 1 月 8 日 09:00 | `05_finance/_tools/yearly-reminder.sh` |

---

## 日志

所有任务的 stdout / stderr 统一写入：

```
/tmp/life-os-launchd.log
```

实时查看：

```bash
tail -f /tmp/life-os-launchd.log
```

注意 `/tmp/` 在 macOS 重启时会被清空——这是设计意图：日志只用于"刚刚跑出问题"的实时排查。**长期"是否曾触发过"的事实源走各模块的 `.manifest.json`**（`cron.<reminder>.last-run` 字段 + git commit 历史），不依赖此日志。

---

## 路径硬编码与跨机器迁移

所有 plist 的 `ProgramArguments` 写死了 `/Users/USERNAME/life-os/...`。这是 user-specific 配置，不可移植。

若要迁到另一台 macOS（例如换电脑）：

```bash
# 把 plist 里的家目录批量替换
sed -i.bak "s|/Users/USERNAME/life-os|$HOME/life-os|g" ~/life-os/.tools/launchd/*.plist
rm ~/life-os/.tools/launchd/*.plist.bak
# 重新执行"首次安装"第 3 步
```

`notify.config.private.json` 不在 git 里（`.gitignore`），需在新机器手工创建（按"首次安装"第 1 步）。

---

## 为什么用 launchd，不用 crontab

1. **macOS 原生**：launchd 是 macOS 的系统级进程管理器（PID 1），Apple 官方推荐的调度方式。crontab 在 macOS 上已属遗留技术，Apple 不再主动维护其集成。

2. **无 TCC 权限限制**：cron 作业在某些 macOS 版本（Catalina+）下会触发 TCC（透明度、同意与控制）弹窗，或因沙盒限制导致文件访问失败。launchd UserAgents 以当前用户身份运行，继承正常的用户权限，不受此影响。

3. **更丰富的调度语义**：`StartCalendarInterval` 支持按 Month/Day/Weekday/Hour/Minute 任意组合，以及数组形式的多时刻配置（季度任务使用）；crontab 的五字段语法无法直接表达"每季度首月第 N 天"这类逻辑。

4. **开机自启与电源管理集成**：launchd agents 开机后自动加载，机器从睡眠唤醒后若错过触发时间，launchd 会在下次满足条件时补触发（可配置）。crontab 错过的任务直接丢失。
