# 分布式系统学习 Lab

[中文课程](https://lynnlee1229.github.io/distributed-systems-lab/zh/) · [English](README.md)

七章原创课程，从系统与故障假设出发，依次学习时间/因果、复制/一致性、Raft/多数派、RPC 超时与幂等、租约与 fencing、恢复与证据。每章有目标、前置、例子/图、任务、解释、自测答案和原始引用，不依赖特定业务背景。

三类真实实验各保留三次基线：etcd Leader 崩溃/原目录重启以及一个或两个投票节点不可响应；提交后延迟响应导致超时，比较普通递增与原子去重；租约过期后恢复旧工作者，比较带/不带 fencing 的下游写。浏览器单寄存器历史检查器是独立的有限模型，不冒充集群实测。

```sh
python3 scripts/install_etcd.py
python3 scripts/run_all.py --repeats 3 --out build/my-results
node tests/checker.test.mjs
python3 -m unittest discover -s tests -v
python3 scripts/build_site.py
python3 scripts/check_site.py
python3 -m http.server 18915 --directory build/site
```

Python 3.11+、Node.js 18+，支持 macOS/Linux arm64/amd64。无需 Docker、API Key、付费服务或 Python 第三方依赖。打开 `/distributed-systems-lab/zh/`。安装器核对固定 etcd 3.6.6 官方附件哈希；有意替换基线时使用 `--out results`，否则新运行与已提交基线分离。CI 在 Linux 另跑一次。

三节点是同一主机的真实进程与独立 WAL，不代表多机性能或生产可用性。故障只作用于本任务进程，不更改宿主网络；进程暂停不等于完整数据包分区。超时结果未知，恢复后记录核对值。未执行磁盘毁坏、灾难还原、2PC 或外部副作用恰好一次。

去重记录与计数器在同一 etcd 事务提交，基线不清理操作键。下游最高 token 与值在同一 SQLite 事务检查更新。Fencing 仅在见过新 token 后拒绝旧代次，不去重同代次请求，也不自动证明当前持锁；恢复集群前必须规划 token 的 epoch/revision。

检查器只支持初值 0 的单整数寄存器、已完成且处于可比时间轴上的读写、每客户端无重叠调用；上限 12 个操作，默认 50,000 个搜索状态，最大 100,000。穷尽才报告失败，达到限制报告未判定，不处理未完成请求、多键事务或锁模型。

原始日志与运行数据只留在忽略的 build/；白名单导出站点与下载包。仅独立学习配套项目公开，个人主页源码私有。原创内容 MIT 授权，第三方论文只链接、不打包。验证范围见 VALIDATION.md。
