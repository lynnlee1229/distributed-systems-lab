"""Original bilingual case briefs, inline activities and semantic diagrams."""
from html import escape

def tr(lang,en,zh):return zh if lang=='zh' else en
ACTIVITIES=[
 ('uncertainty','The missing receipt','消失的回执','01-assumptions','A caller times out. Did the write happen?','客户端超时了，写入究竟发生了吗？'),
 ('causality','Who could know what?','谁可能知道什么？','02-time','Select two events and trace their causal path.','选两个事件，追踪它们之间的因果路径。'),
 ('history','Move a read through time','把一次读拖过时间线','03-consistency','Drag a read across a write and see the model verdict change.','把读拖过写入边界，观察一致性判定如何变化。'),
 ('quorum','Break a three-node cluster','拆掉一个三节点集群','04-consensus','Pause voters, replace the leader and try to commit.','暂停投票节点、替换 Leader，再尝试提交。'),
 ('retries','One intent, two effects?','一个意图，两次效果？','05-retries','Change the response delay and compare retry identities.','改变响应延迟，比较相同和新重试 ID。'),
 ('fencing','The worker that came back','恢复运行的旧工作者','06-fencing','Expire a lease, then decide which worker reaches the sink first.','让租约过期，再决定谁先到达下游。'),
 ('replay','Walk through a real run','逐步读懂一次真实运行','07-recovery','Replay selected observations from all three saved repetitions.','逐步回放三次保存运行中的指定观测。')]

def activity(lang,key,embedded=False):
    item=next(x for x in ACTIVITIES if x[0]==key);_,en,zh,chapter,suben,subzh=item
    real=key=='replay'
    badge=tr(lang,'SAVED REAL EVIDENCE' if real else 'INTERACTIVE TEACHING MODEL','真实保存证据' if real else '可操作的原理模型')
    foot=tr(lang,'Ordered summaries from the saved JSON, not a packet-level replay.' if real else 'Runs in your browser with synthetic state. This is not a live etcd cluster.','来自保存 JSON 的有序摘要，不是逐包回放。' if real else '合成状态在浏览器内运行，不是真实 etcd 集群。')
    anchor='quorum' if key=='quorum' else 'retry' if key=='retries' else 'fencing' if key=='fencing' else 'main'
    return f'<section class="demo-shell" data-demo="{key}" id="demo-{key}"><div class="demo-heading"><span class="demo-badge">{badge}</span><h2>{tr(lang,en,zh)}</h2><p>{tr(lang,suben,subzh)}</p></div><div class="demo-mount"><p>{tr(lang,"Loading activity… Enable JavaScript to interact; the course text remains readable.","正在加载互动… 交互需要 JavaScript；正文仍可直接阅读。")}</p></div><p class="demo-scope">{foot} <a href="{chapter}.html">{tr(lang,"Read the concept","阅读原理")}</a> · <a href="evidence.html#{anchor}">{tr(lang,"Inspect real evidence","查看真实证据")}</a></p></section>'

def playground(lang):
    choices=''.join(f'<a class="scene-choice" href="#{key}" data-scene="{key}"><span>{i+1:02}</span>{tr(lang,en,zh)}</a>' for i,(key,en,zh,*_) in enumerate(ACTIVITIES))
    panels=''.join(f'<div id="{x[0]}" data-scene-panel="{x[0]}" {"" if i==0 else "hidden"}>{activity(lang,x[0])}</div>' for i,x in enumerate(ACTIVITIES))
    return f'<p class="lede">{tr(lang,"Try a decision. Watch the consequence. Then explain why.","先做一次选择，看看会发生什么，再解释为什么。")}</p><p>{tr(lang,"Seven short activities connect the whole course. Pick a scene, change one condition, and compare the outcome. Every scene includes a concrete challenge and immediate feedback.","七个短场景贯穿整门课。选一个场景，改变一个条件，对照结果。每个场景都有具体挑战与即时解释。")}</p><nav class="scene-picker" aria-label="{tr(lang,"Choose an activity","选择互动场景")}">{choices}</nav>{panels}'

CASES={
'01-assumptions':('A configuration editor loses its save receipt. Refreshing shows the new value—but at the timeout the editor did not know that yet. Try three hidden server outcomes with the same caller observation.','配置编辑器保存后没收到回执。刷新时看到了新值，但在超时那一刻，它还不知道结果。试试客户端观测相同的三种服务端情形。'),
'02-time':('A sends a configuration update to B; B forwards a derived update to C. A later local event has no path to B’s earlier independent event. Click the pair and discover which comparisons are justified.','A 给 B 发配置更新，B 再把衍生更新发给 C。A 后来的本地事件与 B 较早的独立事件之间却没有路径。点选事件，看看哪些先后判断有依据。'),
'03-consistency':('A writes the room temperature setting to 1. B reads 0. Move B’s read from inside the write interval to after the success response. The value is unchanged; the legality changes.','A 把房间温控设置写成 1，B 读到 0。把 B 的读从写入过程中拖到成功响应之后：返回值没变，是否合法却变了。'),
'04-consensus':('Three replicas store a shared feature flag. First save version 1, then pause the leader. Can the other two accept version 2? What changes if only one voter remains?','三个副本保存共同的功能开关。先保存版本 1，再暂停 Leader。另两个能接受版本 2 吗？如果只剩一个投票者呢？'),
'05-retries':('A counter button receives no receipt and is clicked again. Both requests can commit. Try a faster response, a longer deadline, and a retry that accidentally uses a new operation ID.','计数按钮没有收到回执，于是又点了一次。两个请求都可能提交。试着加快响应、延长等待，再看看重试时误换一个操作 ID 会怎样。'),
'06-fencing':('Two workers generate the same report file. A pauses, its lease expires, and B writes a newer report. When A resumes, should its old result overwrite B’s? Now reverse which request reaches the sink first.','两个工作者生成同一个报告文件。A 暂停后租约过期，B 写出新报告。A 恢复时，旧结果能否覆盖 B？再反过来，让 A 先到下游。'),
'07-recovery':('A caller saw a timeout while two voters were paused. After they resume, the attempted value is present. Read this as evidence of an unknown outcome, not as a contradiction.','两个投票者暂停时，调用者看到了超时；节点恢复后，尝试写入的值却存在。它是未知结果的证据，不是前后矛盾。')}

def case_brief(lang,slug):
    en,zh=CASES[slug]
    return f'<aside class="case-brief"><span>{tr(lang,"A CONCRETE CASE","先看一个案例")}</span><p>{tr(lang,en,zh)}</p></aside>'

def diagram(lang,slug):
    # Original flow diagrams. The prose beneath each retains the exact guarantee boundary.
    data={
    '01-assumptions':([('Send request','发送请求'),('No receipt','没有回执'),('Unknown','结果未知')],('The server may be waiting, committed, or crashed.','服务端可能尚未处理、已经提交，或已经崩溃。')),
    '02-time':([('A sends','A 发送'),('B receives','B 接收'),('C receives','C 接收')],('Message edges plus local order form a partial order.','消息边与进程内顺序共同形成偏序。')),
    '03-consistency':([('write(1)','写入 1'),('success','成功响应'),('read → 0','读取 0')],('A read that starts after the completed write cannot return 0 in this register’s linearizable history.','在线性一致寄存器历史中，写完成后才开始的读不能返回 0。')),
    '04-consensus':([('Propose','提出命令'),('Majority','多数派确认'),('Apply','按序应用')],('This flow omits Raft’s term, log and election safety rules; read the chapter for those requirements.','流程省略了 Raft 的 Term、日志与选举安全规则；完整要求见正文。')),
    '05-retries':([('Commit effect','提交效果'),('Receipt lost','回执丢失'),('Retry same ID','同 ID 重试')],('Effect and operation result must share an atomic boundary.','副作用与操作结果必须处于同一原子边界。')),
    '06-fencing':([('A: token 10','A：代次 10'),('B: token 11','B：代次 11'),('Reject 10','拒绝代次 10')],('The receiving resource checks the token together with its write, after observing the newer generation.','接收资源见过新代次后，把 token 检查与写入原子执行。')),
    '07-recovery':([('Known success','已知成功'),('Recover','恢复'),('Reconcile','核对未知')],('Preserve acknowledged decisions and separately reconcile timed-out calls.','保留已确认的决策，单独核对超时调用。'))}
    nodes,caption=data[slug];parts=[]
    for i,(en,zh) in enumerate(nodes):
        x=15+i*235;fill=['#e0e9df','#f4e4cb','#edd6ce'][i]
        parts.append(f'<rect x="{x}" y="20" width="205" height="66" rx="9" fill="{fill}"/><text x="{x+102}" y="60" text-anchor="middle" fill="#1e2c2c" font-size="17">{escape(tr(lang,en,zh))}</text>')
        if i<2:parts.append(f'<path d="M{x+210} 53h19m-6-5 6 5-6 5" fill="none" stroke="#657771" stroke-width="2"/>')
    label=escape(tr(lang,*caption))
    return f'<figure class="concept-figure"><svg viewBox="0 0 710 110" role="img" aria-label="{label}" xmlns="http://www.w3.org/2000/svg">{"".join(parts)}</svg><figcaption>{label}</figcaption></figure>'
