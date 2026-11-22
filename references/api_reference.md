# 豆包签到接口参考

排查失败时读；正常签到不需要。

## 两个接口

均为 POST，同源 `https://www.doubao.com`，靠会话 cookie 鉴权，无 a_bogus / msToken 签名。

| 用途 | 地址 | Body |
|---|---|---|
| 查询签到状态（任务面板） | `/alice/ug/campaign/v3/detail/` | `{"campaign_group_code":"pc_incentive_task_mvp_v3"}` |
| 领取签到额度 | `/alice/ug/campaign/landing/checkin` | `{"scene":"pc_incentive_task_mvp_v3"}` |

公共 Query 参数：

```
version_code=23610&language=zh&device_platform=web&doubao_device_platform=web
&aid=497858&real_aid=497858&pkg_type=release_version&pc_version=2.36.10
&doubao_pc_version=5.72.66&samantha_web=1&web_platform=desktop
&use-olympus-account=1&web_tab_id=0&device_id=&region=&sys_region=
```

`version_code` = 本机 `%LOCALAPPDATA%\Doubao\Application\Doubao.exe` 版本按 `major*10000 + minor*100 + patch` 换算（2.36.10 → 23610）。服务端会校验，过期会返回 `710010702`。

## 返回字段

detail：

```json
{"code":0,"data":{"tasks":[{"task_kind":"daily_signin",
  "daily_checkin":{"checked_in_today":true,"continuous_days":1,
    "reward":{"reward_amount":400}}}],
 "progress":{"total_amount":1100}}}
```

checkin 成功：

```json
{"code":0,"data":{"checked_in":true,"checkin_date":"2026-11-23",
 "continuous_days":1,"idempotent":false,"reward_amount":400}}
```

`idempotent:true` 表示今天已领过（服务端幂等，不重复发放）。

## 错误码

| code | 含义 | 处理 |
|---|---|---|
| 0 | 成功 | — |
| 710012001 | 登录已过期 | 让用户重新登录豆包后重跑 |
| 710010702 | 系统错误，通常为 `version_code` 不匹配 | 用本机客户端最新版本重算，脚本已自动处理 |
| 其它非 0 | 活动下线 / 账号不支持 / 风控 | 把 `msg` 原文报给用户，不要重试超过 2 次 |

## 已知边界

- 仅个人账号；企业号 / 飞书账号无此任务，`tasks` 里找不到 `daily_signin`。
- 活动页 UI 有「仅支持豆包电脑版」的前端墙，接口不校验这一点。
- 签到额度：平日 +200，周一（活动翻倍日）+400；当日额度当日 24:00 清零。
- 非公开接口，厂商随时可能变更。
