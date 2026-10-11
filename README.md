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

### Citation stub

See `PAPER_STATUS.md`.

### Layout

```
code/       toy env, GRU A2C (return-std), RNN A2C, ES helpers, S1h2 ES fix, runners
frozen/     clean_seeds_Dx2 + thresholds S1g/S1h2/S1f2 (+ sha256)
results/    summary_S1g.json, summary_S1h2.json, summary_Dx2.json  (no genes)
docs/       权威进度表 excerpt/copy, 回程摘要_S1g/S1h2, 后续方向_半自主与外部暗示
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

### 引用

见 `PAPER_STATUS.md`。论文状态：**内部预注册产物，尚未同行评议**。
