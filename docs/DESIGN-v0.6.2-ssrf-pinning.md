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

## 四、实现中撞到的真实坑

设计对了不等于实现对了。以下几处都是「API 契约与直觉不一致」或「门禁自己说谎」，
写下来是为了下次不再重踩。

### 4.1 `urllib` 的 `do_open` 签名是 `do_open(http_class, req)`

`HTTPHandler.http_open` 调用的是 `self.do_open(http.client.HTTPConnection, req)`。
按 `do_open(self, req)` 写会在运行期抛
`TypeError: do_open() takes 2 positional arguments but 3 were given`。

### 4.2 `Request` 没有 `.port`

`req.host` / `req.type` 有，**`.port` 没有**。端口要从 `req.full_url` 解析：
`urllib.parse.urlsplit(req.full_url).port or 80`。

### 4.3 HTTPS 只能用「换 socket 工厂」，不能改 `conn.host`

`http.client.HTTPSConnection.connect()` 用 `self.host` **同时**决定
**连接目标**和 `server_hostname`（SNI 与证书校验名）。这带来一个陷阱：

直觉写法是「按 IP 构造连接，再把 `conn.host` 改回真实主机名」——
**这是错的**。`connect()` 读的就是 `self.host`，改回主机名等于把 socket
送回一次全新的 DNS 解析，钉住的地址被丢弃，原缺陷在 TLS 上原样复现。
v0.6.2 发布的代码正是这样写的。

正确做法：**不碰 `self.host`，改掉 socket 工厂**——

```python
def _dial(addr, timeout, source=None, _ip=ip_text):
    return socket.create_connection((_ip, port), timeout)

conn = http.client.HTTPSConnection(ip_text, port, context=ctx)
conn._create_connection = _dial   # 连接走已校验 IP
conn.host = host                  # SNI / 证书名走真实主机名
conn.connect()                    # 顺序：先钉 socket，再交名字给 TLS
```

顺序不能反：`conn.host` 必须在 `connect()` **之前**赋值（否则 SNI 拿到 IP），
而 `_create_connection` 保证 `connect()` 不去重新解析名字。

> 这条如果没测，就会产出一个「HTTP 门禁全绿、HTTPS 抓取 100% 失败」的修复——
> 而那正是 v0.6.2 实际发生的事。
> `tests/test_ssrf_tls_pinning.py` 一次请求同时证明 socket 半与 TLS 半。

### 4.4 代理环境变量（独立审查期间发现，我的初判是反的）

`urllib.request.build_opener` 会安装**默认 `ProxyHandler`**，从环境读
`HTTP_PROXY` / `HTTPS_PROXY`，并排在链首。

**我最初的判断被实测推翻**，此处如实记录：当时认定「设了代理时请求会被代理
抢走、绑定彻底失效」。独立审查用活的本地探针代理实测后**否定了这一点**——
`ProxyHandler.proxy_open` 只是 `set_proxy()` 改写 Request 后重新派发，
真正建 socket 的仍是钉住的 handler，探针一次都没被命中。

真实后果是反过来的：**配置的代理被完全绕过**（出网管控失效、代理后唯一可达的
站点抓不到），且 `set_proxy` 把请求行改写成绝对形式
（`GET http://host/ HTTP/1.1`），大量源站会 400。

修复仍是显式传 `urllib.request.ProxyHandler({})`，但**理由是
「intake 抓取刻意不走环境代理」**，不是「防止代理吃掉绑定」。
本机要注意：Windows 注册表里也配了代理，清掉环境变量并不生效。

### 4.5 第一版门禁自己有个假断言

`assert SECRET not in str(exc)` 写成了 bytes 与 str 比较，抛
`TypeError: 'in <string>' requires string as left operand`。断言根本没执行——
**门禁自己的 bug**，不是产品缺陷。但它意味着「私网字节没进内存」这条其实没被检查。

### 4.6 一个更微妙的发现：门禁第一版是**假绿**的

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

## 六、怎么证明做对了

三层，缺一不可：

1. **门禁**（11 条，见第八节）——覆盖拒绝路径、成功路径、TLS 端到端与接线
2. **反向验证**——摘掉修复门禁必须变红；已实测通过
3. **变异测试**——故意破坏实现，确认门禁会红（第九节，5/5）

> 只做第 1 层是不够的。v0.6.2 发布时 6 条门禁全过，
> 而三个阻断级缺陷同时存在——**门禁在坏代码上也是绿的**。

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
| 2 | **反向验证**：摘掉绑定逻辑门禁变红，恢复后全绿 | ✅ |
| 3 | 逐跳重定向各自绑定 | ✅ 由 `_call_transport` 逐跳传入本跳 `before_ips` 保证 |
| 4 | https 证书校验不被破坏 | ✅ `test_ssrf_tls_pinning.py` 端到端 |
| 5 | 现有 intake 测试零放宽 | ✅ 全过，未改动任何既有断言 |
| 6 | 全量回归 | ✅ **414 passed / 1 skipped**（v0.6.1 为 403） |
| 7 | **变异测试 5/5 全部捕获** | ✅ 见第九节 |

### 门禁清单（11 条）

`tests/test_ssrf_connection_pinning.py`（10 条）

| 用例 | 作用 |
|---|---|
| `test_a_pinned_fetch_actually_returns_the_body` | **成功路径**：真起服务，断言 200 与正确 body |
| `test_the_request_line_is_a_path_not_an_absolute_url` | 请求行必须是 `GET /path`，不是代理导致的绝对形式 |
| `test_public_answer_does_not_reach_loopback` | 核心 TOCTOU 门禁，走真实 socket |
| `test_https_pinning_keeps_the_ip_as_the_connect_target` | 断言连接层收到的目标是 IP 字面量 |
| `test_https_handler_accepts_the_context_keyword` | 断言 `do_open` 接受 urllib 必传的 `context` |
| `test_loopback_is_refused_before_any_connection` | 字面 loopback 在连接前就被拒 |
| `test_validate_url_reports_the_ips_it_vetted` | 确认校验层确实返回了地址清单 |
| `test_default_transport_accepts_a_pinned_address` | 断言接线缝隙存在 |
| `test_pinned_handlers_replace_the_default_ones` | 断言绑定 handler 在链上，且 stock handler 不在 |
| `test_opener_has_no_proxy_handler_in_front_of_the_pinned_ones` | 断言环境代理不能抢在绑定之前接管请求 |

`tests/test_ssrf_tls_pinning.py`（1 条）

| 用例 | 作用 |
|---|---|
| `test_a_pinned_https_fetch_succeeds_with_real_sni_and_cert` | **TLS 端到端**：真证书 + 真 socket，一次请求同时证明 socket 半与 TLS 半 |

---

## 九、变异测试：门禁自己说过五次谎

`.codex_tmp/mutate_verify.py` 故意破坏实现，确认门禁会红。
**在坏代码上仍然是绿的门禁不是门禁**，所以这一节是本文最重要的一节。

最终结果：**5/5 全部捕获**

| 变异 | 结果 |
|---|---|
| M1 headers 传到 body 位 | CAUGHT（2 failed） |
| M2 `do_open` 不接受 `context` | CAUGHT（3 failed） |
| M3 TLS 丢失主机名（SNI 消失） | CAUGHT（1 failed） |
| M4 代理回到绑定 handler 之前 | CAUGHT（1 failed） |
| M5 去掉钉住，改为按主机名连接 | CAUGHT（1 failed） |

### 它翻出来的五个问题，每一个都是「门禁在说谎」

1. **只有拒绝型测试**。最初的 6 条里没有一条让抓取成功返回过 body。
   「该拒绝的拒绝了」和「彻底坏了」在这个套件里长得一模一样。
2. **`pytest.skip` 自我放行**。连接层没被观察到时门禁选择跳过，
   而跳过就是绿灯——M3 因此漏了两轮。
3. **源码文本断言锁死了有害代码**。
   `assert "conn.host = host" in inspect.getsource(...)` 把**引入缺陷的那一行**
   固化成了要求。变异证明它连一行注释都能满足。
4. **TLS 测试的场景区分不出真伪**。测试用 `https://localhost` 配
   `ips=["127.0.0.1"]`，而 `localhost` 本就解析到 127.0.0.1——「按主机名连」
   和「按钉住 IP 连」结果完全相同。**它在坏代码上也是绿的。**
5. **测试证书自己补上了漏洞**。证书同时签了 `DNS:pinned.example` 与
   `IP:127.0.0.1`，于是「丢掉主机名、改为对着地址校验」照样通过。
   改成只签 DNS 名后，M3 才被抓住。

> 五个问题里有三个是我自己写的门禁在坏代码上报绿。
> **这就是为什么「11 条全过」不能作为提交依据**——变异测试才是。
>
> 另一个反复出现的形状：修好一处之后我曾两次宣布「已补强」，
> 下一轮变异又翻出新的。门禁的加固是迭代的，不是一次性的。

---

## 十、发布状态

- v0.6.2 tag `v0.6.2` → commit `8eeaaf5`，**已发布，且带着上述三个缺陷**
  （CI 五 job 全绿、39 个附件字节校验全过、元数据门禁通过——这些都不能证明功能可用）
- 本次修正未打 tag；补发补丁需显式授权

> 两次同形状事故：v0.6.0 的 Windows 便携包「四个 job 全绿、全部测试通过、
> 一启动就崩」，以及本次的「全绿、但抓取 100% 失败」。
> **建议 v0.7 开工前先补一条 CI 门禁：每个关键功能路径必须有一条
> 「成功执行」测试，而不只有「该拒绝的拒绝了」这一类。**