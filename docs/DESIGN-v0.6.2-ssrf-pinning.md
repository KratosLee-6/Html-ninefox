# v0.6.2 安全补丁 · 设计：SSRF 连接级 IP 绑定（P1-6）

> 建立时间：2026-10-04
> 基线：`v0.6.1` tag → commit `0585b9d`（2026-10-03 发布）
> 状态：**已实现，门禁反向验证通过**。本文记录「要做什么、为什么、怎么证明做对了」，
> 第五节记录实现中撞到的真实坑——那三处都不是设计错，是 API 契约与直觉不一致。

---

## 一、缺陷是什么（已核实，不是推测）

`htmlninefox/intake.py`：

```python
def fetch_reference(url, *, ..., transport=None, resolver=None):
    for _ in range(max_hops + 1):
        _, host, before_ips = validate_url(current_url, resolver)   # L188
        status, resp_headers, body = transport(current_url, headers or {}, timeout, max_bytes)  # L189
```

`validate_url` 解析主机、拒绝一切非公网 IP，并把 `before_ips` 返回给调用方
（`intake.py:127-140`）。**但 `before_ips` 在 `fetch_reference` 里从未被使用。**

`transport` 的默认实现 `_default_transport`（L151-167）构造 `urllib` opener 并
直接 `opener.open(request)`，由 `urllib` 自行做第二次 DNS 解析并连接。

因此存在一个 **TOCTOU 窗口**：

```
t0  validate_url()  →  解析 example.com → 93.184.x.x（公网，通过）
t1  urllib 建连     →  再次解析 example.com → 127.0.0.1（已被 rebinding 换掉）
t2  响应到达        →  _resolve() 比对，发现变了 → 丢弃响应
```

L199-203 的「响应后重新解析比对」是**事后检测**，不是**事前防护**。
它能发现 rebinding，但**字节已经通过一条通往私网的连接流进来了**，
并且这段字节会进入内存、可能进入落盘的证据目录。

> 现有代码的文档字符串（`intake.py:6-8`）写的是
> 「re-resolved after the response arrives so DNS rebinding cannot swap in a
> private target mid-flight」。**这句话是不准确的**——它做到的是「发现后丢弃」，
> 不是「cannot swap in」。这个偏差本身就是缺陷的一部分：读代码的人会以为已经防住了。

### 现有测试为什么没抓到

`tests/test_design_intake.py::test_fetch_detects_dns_rebinding` 用的是
`ok_transport()` ——一个返回固定字节的假传输，只断言解析结果变化会被发现。
**没有任何一条测试验证真实连接连到了哪个 IP**。也就是说：只要 `validate_url`
还在跑，无论实际连到哪里，这组测试全绿。

这是本项目反复出现的形状——**两边都在，但没人保证它们一致**（C3/C4 同一形状）。

---

## 二、为什么现在做

v0.6 只有 12 个内置源，暴露面有限，且已在 `RELEASE-NOTES-v0.6.0.md` 中公开披露为
残余风险。**v0.7 要做「粘贴任意网址 → 拆解」，那条入口让用户直接输入任意 URL，
SSRF 的暴露面从「12 个已知站点」变成「任何地址」**。届时再补就是拿新功能去赌。

所以排期是：**先出 v0.6.2 安全补丁，再开 v0.7**。

---

## 三、方案

### 3.1 核心：让连接绑定到「已校验的那个 IP」

`validate_url` 已经返回了 `ips`。缺的是**把这个 IP 交给传输层**。

新建 `_PinnedHTTPHandler` / `_PinnedHTTPSHandler`，基于 `http.client`：

- 用**已校验的 IP** 作为实际 TCP 连接目标
- `Host` 头仍用原始主机名（虚拟主机必需）
- HTTPS 时 **SNI 与证书校验仍用原始主机名**，只换连接目标

这是唯一能真正关闭 TOCTOU 的做法：校验和连接用**同一个 IP**，中间没有第二次解析。

> 不采用「校验后 monkey-patch 解析器缓存」这类方案——它把第二次解析换成第一次解析，
> 但仍是两次解析，仍有窗口。

### 3.2 逐跳重新绑定

重定向的每一跳都独立走「校验 → 连接」，因此每一跳都各自绑定。
第 N 跳的 IP 不复用第 N−1 跳的。

### 3.3 保留响应后比对

L199-203 的检查**保留不删**。它现在不再是唯一防线，而是纵深防御的第三层：
绑定（防 TOCTOU）→ 连接即校验 → 响应后比对（检测 rebinding）。

### 3.4 失败模式必须是稳定的错误码

新增/复用的错误码要让调用方能区分：
`intake_host_forbidden`（解析到私网）/ `intake_connect_failed`（连不上被绑定的 IP）。

---

## 五、实现中撞到的三处真实坑

设计对了不等于实现对了。以下三处都是「API 契约与直觉不一致」，写下来是为了下次
不再重踩。

### 5.1 `urllib` 的 `do_open` 签名是 `do_open(http_class, req)`

`HTTPHandler.http_open` 调用的是 `self.do_open(http.client.HTTPConnection, req)`。
按 `do_open(self, req)` 写会在运行期抛
`TypeError: do_open() takes 2 positional arguments but 3 were given`。

### 5.2 `Request` 没有 `.port`

`req.host` / `req.type` 有，**`.port` 没有**。端口要从 `req.full_url` 解析：
`urllib.parse.urlsplit(req.full_url).port or 80`。

### 5.3 HTTPS 不能走同一个 helper

`http.client.HTTPSConnection.connect()` 用 `server_hostname=self.host` 做 SNI，
证书校验也取 `self.host`。**如果按 IP 构造再把 `self.host` 设成 IP，SNI 和证书
就都对着地址校验了**——每个虚拟主机站点都会证书不匹配。

正确做法：连接对象对 IP 构造（socket 去 IP），随后把 `conn.host` 改回真实主机名，
再 `connect()`。这也是为什么 `_pin_http_connection` 只服务明文 HTTP，
TLS 必须留在 `_PinnedHTTPSHandler` 里单独处理。

> 这条如果没测，就会产出一个「HTTP 门禁全绿、真实 HTTPS 抓取全崩」的修复。
> `test_https_pinning_keeps_the_real_hostname_for_sni` 就是为它写的。

### 5.4 附带一处：第一版门禁自己有个假断言

`assert SECRET not in str(exc)` 写成了 bytes 与 str 比较，抛
`TypeError: 'in <string>' requires string as left operand`。断言根本没执行——
**门禁自己的 bug**，不是产品缺陷。但它意味着「私网字节没进内存」这条其实没被检查。

### 5.5 一个更微妙的发现：门禁第一版是**假绿**的

第一版门禁用「固定返回公网 IP」的 resolver。跑出来是**绿的**——因为
`validate_url` 的那次解析就返回了公网，第二次解析也返回公网，`urllib` 连的是
公网地址，自然连不上本机服务。

要暴露窗口，resolver 必须**第一次报公网、第二次报 127.0.0.1**——
即攻击者的真实手法。改完之后旧实现的失败形态是
`intake_fetch_failed: Remote end closed connection without response`，
也就是**它真的去连了私网，只是这次没连上**。

> 门禁红了，但没有以「泄漏了私网内容」的形式红，而是以「连接失败」的形式红。
> 这恰恰说明旧实现的防护是**运气**而不是设计——同一段代码在攻击者的服务器
> 可达时就会拿到私网响应，而响应后比对只能事后丢弃，已经流过的字节收不回。
> 所以门禁断言的是「必须因决策而失败，不能因连接失败而侥幸失败」。

---

## 六、怎么证明做对了（门禁 + 反向验证）

---

## 七、不做什么（避免范围蔓延）

| 不做 | 理由 |
|---|---|
| 不改 12 个内置源的注册方式 | 与本缺陷无关 |
| 不做代理 / 出网白名单 | 超出本版范围，属产品策略 |
| 不动 `LICENSE_CLASSES` 与版权规则 | 那属 v0.7「用户指定网址」的独立许可规则，不属安全补丁 |
| 不重构 `IntakeService`（P1-7） | 结构性债，单独排期 |

---

## 八、验收判据与实际结果

| # | 判据 | 结果 |
|---|---|---|
| 1 | 真实 socket 门禁：解析器先报公网、后报 127.0.0.1 时必须失败 | ✅ |
| 2 | **反向验证**：摘掉绑定逻辑门禁变红，恢复后全绿 | ✅ 实测通过 |
| 3 | 逐跳重定向各自绑定 | ✅ 由 `_call_transport` 逐跳传入本跳 `before_ips` 保证 |
| 4 | https 证书校验不被破坏 | ✅ `test_https_pinning_keeps_the_real_hostname_for_sni` |
| 5 | 现有 intake 测试零放宽 | ✅ 62 条全过，未改动任何既有断言 |
| 6 | 全量回归 ≥403 通过 | ✅ **409 passed / 1 skipped**（403 基线 + 6 条新门禁） |

### 门禁清单（`tests/test_ssrf_connection_pinning.py`，6 条）

| 用例 | 作用 |
|---|---|
| `test_public_answer_does_not_reach_loopback` | 核心 TOCTOU 门禁，走真实 socket |
| `test_loopback_is_refused_before_any_connection` | 字面 loopback 在连接前就被拒 |
| `test_validate_url_reports_the_ips_it_vetted` | 确认校验层确实返回了地址清单 |
| `test_default_transport_accepts_a_pinned_address` | 断言接线缝隙存在 |
| `test_pinned_handlers_replace_the_default_ones` | 断言绑定 handler 真的挂进了 opener |
| `test_https_pinning_keeps_the_real_hostname_for_sni` | 断言 SNI 没被绑定到 IP 上 |

后三条是**接线门禁**：它们防的是「代码看起来修好了，但没接到链路上」——
这正是 C3 / C4 / 「导出中心从来没有 PPTX 选项」的同一形状。

---

## 九、发布策略

补丁版本，**tag 需显式授权**。发布说明必须写明：
本版关闭的是**已公开披露**的残余风险，而非新发现的漏洞；
并记录 v0.6.0 披露以来该风险的实际暴露面（12 个内置源），
以及 v0.7「用户粘贴任意网址」会把这个暴露面放大的事实。
