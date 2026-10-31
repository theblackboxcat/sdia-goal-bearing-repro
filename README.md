# sdia-goal-bearing-repro

Slim public reproduction package for the **non-creationism goal-bearing** toy line  
(S1f2 return-std fix → Dx2 leak ruler → S1g clean-seed confirm → S1h2 ES select fix).

**Author:** 李逾凡 (Li Yufan)  
**Repo:** https://github.com/theblackboxcat/sdia-goal-bearing-repro  
**License:** MIT  
**Status:** internal preregistration artifacts; **not peer-reviewed** (see `PAPER_STATUS.md`).

---

## English

### What this reproduces

| Piece | Role |
|-------|------|
| **S1g** | Clean Dx2 seeds: GRU+A2C (return-only, **fixed return std**) **8/8** vs tanh-RNN **0/8**; L2-self lands in **gated architecture** bin. |
| **Dx2** | Leak-probe calibration; frozen clean science seeds `[200,205,210,211,212,216,218,219]`. |
| **S1h2** | OpenAI-ES **standard step** + **selection fix**; easy **8/8**, main **4/8** → repaired ES is a valid ruler; **under matched budget, evolution did not reach**. |

Frozen thresholds (+ sha256), summary JSON only (no genes), and core code paths from the internal `必要性重建` tree.

### How to run

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 1) S1g toy confirm + Dx2 seed list + S1h2 ES note (smoke GRU A2C)
python code/toy_confirm.py

# 2) Optional: S1g single-arm smoke (writes under package logs/genes/)
python code/run_s1g_arm.py --arm G_RL_GRU --seed 200 --smoke

# 3) Inspect frozen Dx2 seeds / S1h2 note without training
python code/toy_confirm.py --skip-train
```

Full science re-runs need the frozen protocols in `frozen/` (acceptance C1–C6, leak VOID mean>0.35 → VOID, denom=8). This slim package prioritizes auditability over shipping gene dumps.

**S1h2 ES code:** `code/s1h2_es_gru.py` (standard step `(lr/σ)·g`; save `best_vec` before θ update; independent K=16 re-eval). A full 24-arm science retrain is **not** bundled; see `results/summary_S1h2.json` and `docs/回程摘要_S1h2.md`.

### Forbid overclaims

- **Do not** write “evolution unreachable” (no budget scan was run).
- **Do not** write “RNN / prior-free unreachable in principle” (RNN was not tuned).
- **Do not** weaken leak VOID **0.35** or shrink VOID denominator from **8**.
- **Do not** treat teacher labels as “necessary” on this toy after S1f2 (teacher ≈ sample efficiency).
- Genes / large checkpoints are intentionally **absent**.
- **禁写数值 p_c 平移** / **Do not transfer a numeric lattice percolation \(p_c\)**: do not claim this protocol’s gating threshold is “≈ 2D site \(p_c\)≈0.5927 / bond 0.5 / 3D 0.3116”, and do not call E2’s 1/8, or the draft figure E2b 3/8, a measured \(p_c\). E2b’s 3/8 is cited from the 2026-10-30 draft only; this package has **no** E2b archive and has **not** verified that count — it is named here only so it cannot be laundered into a critical point. Percolation is only a **critical-skeleton analogy** (order parameter / connectivity threshold / diverging correlation length). Lattice, neighborhood, and occupation are not isomorphic; skeleton analogy ≠ numeric isomorphism. The ceiling is a **falsifiable hypothesis**, not a result: effective occupation crossing a threshold yields register-like hold under this protocol. Pointers: `docs/E2_C4pp_archive_extract_2026-10-30.md`, `docs/P1_occupation_sweep_READOUT_2026-10-31.md`.
- **Do not read cross-seed scatter as a phase diagram**: E2’s eight seeds span `every.dwf/sparse.dwf` ≈ 0.44–1.01 (n=8, 95% CI half-width 0.175). That spread is **seed noise**, not a scanned occupation axis. Do not draw an occupation–order-parameter curve or estimate a critical point from it. Any occupation sweep needs its own preregistration; these notes are not that preregistration.
- **2026-10-31 readout bounds** (external dump, archived only; no run in this package): **`q` is cancelled** (singularity at full cue, non-random missingness, low-\(p\) saturation; the delivered ΔBIC did not meet a ≥10 preference bar). **`sparse.dwf` is exploratory** (order parameter chosen after seeing the data; it does not inherit confirmatory status). **Do not claim a percolation \(p_c\)**. **S3 remains CLOSED**. **No new science runs** are authorized. See `docs/P1_occupation_sweep_READOUT_2026-10-31.md`.

> Reading ceiling (2026-10-30): C4″ “directional 8/8 ∧ specific 3/8” (E2 archive restatement in `docs/E2_C4pp_archive_extract_2026-10-30.md` only) may be a **candidate** near-critical bottleneck reading — local specificity present, global hold not through. It is **not** a \(p_c\) measurement and **not** a theorem. Specificity and functional return do not covary (only seed 200 clears both C1 and clause iii).

### Citation stub

See `PAPER_STATUS.md`.

### Layout

```
code/       toy env, GRU A2C (return-std), RNN A2C, ES helpers, S1h2 ES fix, runners
frozen/     clean_seeds_Dx2 + thresholds S1g/S1h2/S1f2 (+ sha256)
results/    summary_S1g.json, summary_S1h2.json, summary_Dx2.json  (no genes)
docs/       权威进度表 excerpt/copy, 回程摘要_S1g/S1h2, 后续方向_半自主与外部暗示,
            P2_void_prescreen_2026-10-30.md, E2_C4pp_archive_extract_2026-10-30.md,
            PROBE_AUDIT_leak_2026-10-30.md, P1_occupation_sweep_READOUT_2026-10-31.md
tools/      analyze_v2.py  (exploratory readout of an external sweep dump; no training)
```

---

## 中文

### 本包复现什么

| 模块 | 作用 |
|------|------|
| **S1g** | Dx2 干净籽：GRU+A2C（仅世界回报，**回报标准化修复**）**8/8** vs tanh-RNN **0/8**；L2-self 落在**通用门控架构档**。 |
| **Dx2** | leak 探针标定；冻结科学籽 `[200,205,210,211,212,216,218,219]`。 |
| **S1h2** | OpenAI-ES **标准步** + **选择修复**；easy **8/8**、main **4/8** → 修好的 ES 为合格尺子；**同预算下进化未达**。 |

含冻结阈值（+sha256）、汇总 JSON（无基因）、以及内部 `必要性重建` 树中的核心代码路径。

### 如何运行

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 1) S1g 玩具确认 + Dx2 籽列表 + S1h2 ES 说明（GRU A2C smoke）
python code/toy_confirm.py

# 2) 可选：S1g 单臂 smoke
python code/run_s1g_arm.py --arm G_RL_GRU --seed 200 --smoke

# 3) 只看籽列表与 S1h2 说明
python code/toy_confirm.py --skip-train
```

完整科学复跑须遵守 `frozen/` 协议（验收 C1–C6；leak 均值>0.35→VOID；分母=8）。本包以可审计为主，不附带基因文件。

### 禁止过度声称

- **禁写**「进化不可达」（未做预算扫描）。
- **禁写**「无先验 / RNN 原理不可达」（RNN 未调参）。
- **禁止**放宽 leak VOID **0.35** 或缩小 VOID 分母（恒为 **8**）。
- S1f2 之后勿把教师信号写成该玩具上的「必要」（教师≈样本效率）。
- 故意**不包含**基因 / 大型权重。
- **禁止把渗流临界骨架写成数值平移**（**禁写数值 p_c 平移**）：不得声称本协议的门控临界「≈ 2D site \(p_c\)≈0.5927 / bond 0.5 / 3D 0.3116」，也不得把 E2 的 1/8、或草案里的 E2b 3/8，说成「已测得 \(p_c\)」。E2b 的 3/8 引自 2026-10-30 推进草案；本包**无** E2b 归档、**未核验**该计数，此处只用于封顶、不采信。渗流在此仅作**临界骨架类比**（序参量／连通阈值／关联长度发散），晶格、邻域、占据定义均非同构；骨架同构 ≠ 数值同构。允许的上限：本协议下「有效占据跨阈值 → 寄存器式 hold」的**可证伪假说**，本包**未**把它写成已测结果。指针：`docs/E2_C4pp_archive_extract_2026-10-30.md`、`docs/P1_occupation_sweep_READOUT_2026-10-31.md`。
- **禁止把跨籽散布读成相图**：E2 八籽的 `every.dwf/sparse.dwf` 跨 0.44–1.01（n=8，95% CI 半宽 0.175）是**种子噪声**，不是被扫描的占据轴。不得据此画「占据–序参量」曲线或估计临界点。任何占据扫描须另开预注册；本包这些笔记**不是**该预注册。
- **2026-10-31 读出边界**（外部回传，只归档、本包不重跑）：**`q` 作废**（奇点、缺失非随机、低档饱和；交付 ΔBIC 未达到 ≥10 的偏好判据）。**`sparse.dwf` 为探索性**（看到数据后才换的序参量，不继承确认性地位）。**不宣称渗流 \(p_c\)**。**S3 仍 CLOSED**。**不授权新的科学跑**。见 `docs/P1_occupation_sweep_READOUT_2026-10-31.md`。

> 读法上限（2026-10-30 补）：C4″ 的「定向 8/8 ∧ 特异性 3/8」（只复述 E2 归档，见 `docs/E2_C4pp_archive_extract_2026-10-30.md`）可作**渗流近临界**的结构瓶颈**候选**读法（局部特异性已出现、全局 hold 未贯通），但**不是** \(p_c\) 测量，也**不**升格为定理。特异性与功能回报不共变（同时过 C1∧iii 的只有 seed 200）。

### 引用

见 `PAPER_STATUS.md`。论文状态：**内部预注册产物，尚未同行评议**。
