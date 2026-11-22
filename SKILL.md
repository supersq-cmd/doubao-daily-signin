---
name: doubao-daily-signin
description: 完成豆包（doubao.com，即豆包电脑客户端里的「免费用豆包工作」任务页）的每日签到并领取体验额度：查询今天是否已签到、自动领取（平日 +200 额度、周一翻倍 +400）、读取连续签到天数与额度余额并汇报结果；支持把「每天几点签到」写进 config.json 并同步到每日定时任务（可说「每天早上 7 点签到」「签到时间改成 8 点半」「现在是什么时间签到」）。Use when 用户提到 豆包签到、每日签到、领积分、领额度、签到任务、连续签到天数、今天签到了吗、签到时间、免费用豆包工作。不用于 WorkBuddy、Trae、Qoder 等其它产品的签到。
---

# 豆包每日签到

## 原理

豆包「每日签到」是活动组 `pc_incentive_task_mvp_v3` 里 `task_kind=daily_signin` 的一条任务。在**已登录**的豆包页面上下文里调用活动接口即可完成签到——登录态由豆包内置浏览器自动携带，不需要抓包、不需要读 cookie、不需要浏览器数据库。

## 执行步骤

1. 用 `computer_use_tool(plane="bu")` 执行本技能 `scripts/signin.py` 的**全文**作为该单元格 `code`（脚本内已 import `aha_browser_use as bu`，自行处理页面导航、版本号派生、接口调用与结果轮询）。它只打印一行 JSON。
2. 按 JSON 的 `status` 用一句话汇报「日期 + 状态 + 额度」：
   - `checked-in`：签到成功，`+reward_amount` 额度，连续 `continuous_days` 天，当前累计 `total_amount`。
   - `already`：今天已签过，服务端幂等不会重复发放；给出连续天数与余额。
   - `no-activity`：当前账号无签到任务（活动未开放，或企业/飞书账号不支持）。
   - `auth-required`：豆包未登录 —— 立刻调用 `interaction.request_action`（`type="browserControl"`），请用户在浏览器里扫码登录豆包，控制权交回后重跑本技能。
   - `failed`：把 `message` 原文报给用户，**不要**谎报成功。
3. 同一轮最多重试 2 次；签到成功后不要反复调用领取接口。

## 硬性约束

- 只用 `bu` 平面（豆包内置浏览器）。不要改用 Edge/Chrome，不要读 cookie 文件，不要用 shell 直接发 HTTP——那些路径拿不到客户端登录态。
- 若 `bu.page_info()` 的 url 不含 `doubao.com`，先 `bu.navigate("https://www.doubao.com/chat/")` 再执行脚本。
- 单账号、个人账号；不要多账号批量。
- 返回 `710010702` 表示 `version_code` 失效：脚本已按本机 `Doubao.exe` 版本自动派生并回退候选值，仍失败就如实报告接口可能变更。

## 每天自动签到（时间可设置）

签到时间存在技能根目录 `config.json` 的 `signin_time`（默认 `07:20`），问一次、改一次都用 `scripts/schedule.py`：

```bash
python scripts/schedule.py --show          # 查看：{"signin_time":"07:20","cron":"20 7 * * *",...}
python scripts/schedule.py --set 08:30     # 改成 08:30，输出里的 cron 就是定时任务要用的表达式
python scripts/schedule.py --job <id>      # 记下已创建的定时任务 id，便于以后改
```

用户说「每天 7 点签到 / 签到时间改成 8 点半 / 几点签」时的固定流程：

1. 跑 `schedule.py --set HH:MM`（只问不改就用 `--show`），拿到 `cron` 表达式。
2. 还没建过定时任务：用 `create_cron_job` 建一条，`schedule_type="cron"`、`schedule` 取上一步的 `cron`、`runtime_type=2`（**必须本地**，签到依赖本机豆包客户端的登录态，云端跑不了）、`title`「豆包每日签到」、`enable=true`，`query` 写「本次请求是由「豆包每日签到」定时任务到时触发的：用 doubao-daily-signin 技能完成今天的豆包签到，并告诉我是否已签到、领取多少额度、连续第几天」。建完用 `schedule.py --job <返回的 id>` 存回 config。
3. 已有任务：先 `get_cron_job`，再 `update_cron_job`，patch 里只放 `schedule` 和 `schedule_type`。
4. 时间落在 7:30-10:00 / 15:30-17:00 / 19:30-20:00 属于任务高峰期，要提示可能排队晚触发（脚本输出的 `peak_warning` 会直接告诉你）。

执行前提：定时任务触发时豆包客户端需在运行并保持登录；服务端幂等，重复跑不会多领、不会重复扣。

## 汇报格式

每次签到结束固定给一句话：**日期 · 状态 · 获得额度 · 连续天数 · 累计额度**。例如「11-23 今天已签到（此前已领）· 周一翻倍 400 · 连续第 1 天 · 活动累计 1100」。

## 分发 / 发布

对外发布的目录结构固定为：`SKILL.md`、`config.json`、`scripts/`、`references/`，外加 `README.md`（安装说明）、`LICENSE`（MIT）、`install.ps1`（Windows 一键装到 `.user_skills`）。发布包里 `config.json` 的 `cron_job_id` 必须是 `null`，不能带作者本人的任务 id。

## 接口细节

仅在排查失败时读 `references/api_reference.md`。
