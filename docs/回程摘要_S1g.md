# 回程摘要 · S1g 干净籽确认（GRU vs RNN · 2026-10-11 ~15:05 CST）

> 时区 Asia/Shanghai。树：`必要性重建/S1g_clean_confirm/`。新建预注册（非修订 S1f2/Dx2）。
> thresholds sha `9b77a4a5…44ea4`（跑前冻）；clean seeds sha `22263a4f…573f6`；验收复用 S1e `412e0001…8c74`（未削弱）；leak 线 0.35；分母 8。

## 结果（干净籽 [200,205,210,211,212,216,218,219]；VOID 0/40）

| 臂 | 结果 | Wilson 95% |
|----|------|-----------|
| **G_RL_GRU**（A2C return-only） | **8/8 PASS** | [0.676, 1.000] |
| **G_RL_RNN**（tanh 无门，同 A2C/预算） | **0/8** | [0.000, 0.324] |
| C 阳控 | 7/8（实验完整） | [0.529, 0.978] |
| A 阴基 | 0/8 | [0.000, 0.324] |
| ES_GRU（同架构 OpenAI-ES，38400 evals） | 0/8 | [0.000, 0.324] |

## 路由
- 计划 §3：仅 GRU 过 → **L2-self 落「通用门控架构档」**（非无先验档）。
- S1f2「5/8 modulo VOID」保留**解除**：干净籽 8/8。
- 同 GRU：A2C 8/8 vs ES 0/8 → 与「BPTT 信用分配 vs 进化」轴一致（带下列 ES 保留）。

## 诊断（仅日志）
- **RNN 未学习**：训练回报 8 籽合并均值 0.250，全程平坦，800 epoch 无 early-stop；GRU 各籽 ~200–300 epoch 起飞。loss 下降为 value 拟合，非策略改进。代码与 GRU 仅 cell 不同。解读：K=30–70 长程依赖下无门 tanh BPTT 信用分配失效。保留：RNN 未调参、单预算 → 不可写「无先验不可达」。
- **ES 种群均值不动**（0.25→0.25）；best_fit 0.59–0.64 为噪声最大值。**⚠️ 新隐患**：ES 更新 `theta += lr*sigma*grad` 步长为标准 OpenAI-ES 的 σ²≈1/156；S1e 全家族同写法 → ES 0/8 非干净进化对照，禁写「进化不可达」。

## STOP
- **不开 E2**（S1g 计划禁自动开）。E2 G0「L2-self 组过」首次在 GRU 档满足 → **待猫猫授权 + 裁定档位**。
- 候选（未启动）：ES 步长复核重测；RNN 调参籽有限调参后再测；E2。

## 路径
- `必要性重建/S1g_clean_confirm/报告.md` · `logs/summary.json` · `scripts/summarize_s1g.py`
- 已同步：`权威进度表_2026-10-10.md` · `计划_S0-S4.md` · `进度日记.md`（备份 `*_pre_S1g_report.md`）
