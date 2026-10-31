# -*- coding: utf-8 -*-
"""analyze_v2.py — 占据扫描的第二版分析器（修正 analyze_occ.py 的四处缺陷）

为什么换掉 analyze_occ.py
------------------------
1. **q = 1 - every/sparse 有奇点**：p_cue=1.0 时两条臂的 dwf 同时趋于 0，
   比值 0/0 → NaN。全部 40 个 p=1.0 单元因此丢失（占 200 单元的 20%）。
   而 p=0.25 档也有 30% 单元因 sparse 塌到 0 而 NaN，且缺失**非随机**
   （塌陷的单元正是低 q 的单元）→ 幸存者均值被系统性抬高。
2. **伪重复**：analyze_occ.py 把同一 (籽, 档) 的 5 次重复当作 5 个独立样本，
   n 被放大 5 倍，BIC 与 CI 因此过度自信。有效样本量是 40 个格，不是 200。
3. **模型竞争在 3 个 x 上不可识别**：p=1.0 全灭后只剩 0/0.02/0.08/0.25 四档，
   而 0.25 有一半 NaN。二次模型对 3 个不同 x 是精确插值（RSS=0），
   「M2 胜」是结构性的，不是经验证据。
4. **ΔBIC 判据没执行**：预注册要求 ΔBIC ≥ 10 才算有偏好，
   报告在 ΔBIC=0.52 时就宣布了胜者。

本脚本改用两个**处处有定义**的量
--------------------------------
A. `sparse.dwf`（连续，有界 [-1,1]）：潜状态对行为的因果效应强度。
   p=1.0 时它趋于 0，这是**真实效应归零**，不是缺失。
B. 二值「寄存器存活」：`sparse.dwf > cut`。分布是双峰的（0.65 与 0 两簇），
   所以判活线在 0.3–0.6 之间任取，计数几乎不变 —— 这是本量最硬的地方。

纪律
----
- 不再对 q 做任何推断。
- 不做「有/无变点」的二选一；只报剂量–反应曲线与它的 CI。
- 不写 p_c、不写「测到临界」、不写「涌现→智能定律」。
- 本分析是**探索性**的：换了序参量，不继承原预注册的确认性地位。
"""
from __future__ import annotations

import argparse
import collections
import glob
import json
import math
import os
import statistics as st

LEVELS_DEFAULT = (0.0, 0.02, 0.08, 0.25, 1.0)


def fin(x):
    return isinstance(x, (int, float)) and math.isfinite(x)


def wilson(k, n, z=1.96):
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, c - h), min(1.0, c + h))


def load_units(results_dir, tag="sweep"):
    files = sorted(glob.glob(os.path.join(results_dir, f"unit_{tag}*.json")))
    out = []
    for f in files:
        try:
            d = json.load(open(f, encoding="utf-8"))
        except Exception:
            continue
        d["_file"] = os.path.basename(f)
        d["_rep"] = int(os.path.basename(f).rsplit("_r", 1)[-1].split(".")[0])
        out.append(d)
    return out


def section_data_health(units):
    print("=" * 72)
    print("一、数据体检（先看能不能用，再谈结论）")
    print("=" * 72)
    cells = collections.defaultdict(list)
    for u in units:
        cells[(u["seed"], round(u["p_cue"], 4))].append(u)
    levels = sorted({k[1] for k in cells})
    seeds = sorted({k[0] for k in cells})
    print(f"单元 {len(units)} 个 = {len(seeds)} 籽 × {len(levels)} 档 × "
          f"{len(units) // max(len(cells), 1)} 重复（格数 {len(cells)}）")

    print("\n[a] q = 1 - every/sparse 的可定义率")
    for p in levels:
        g = [u for u in units if round(u["p_cue"], 4) == p]
        ok = sum(1 for u in g if fin(u["derived"].get("q")))
        print(f"    p={p:<6g}  q 有定义 {ok:>3}/{len(g):<3}  ({100*ok/len(g):5.1f}%)")

    print("\n[b] sparse.dwf 的可定义率（新序参量）")
    for p in levels:
        g = [u["c4pp"]["sparse"]["dwf"] for u in units if round(u["p_cue"], 4) == p]
        ok = sum(1 for x in g if fin(x))
        print(f"    p={p:<6g}  有定义 {ok:>3}/{len(g):<3}  ({100*ok/len(g):5.1f}%)")

    print("\n[c] 重复格检测：同籽同 rep 在不同档是否逐位相同")
    byrep = collections.defaultdict(dict)
    for u in units:
        byrep[(u["seed"], u["_rep"])][round(u["p_cue"], 4)] = (
            u["c4pp"]["sparse"]["dwf"], u["c4pp"]["every"]["dwf"])
    dup_pairs = collections.Counter()
    for k, v in byrep.items():
        ps = sorted(v)
        for i in range(len(ps)):
            for j in range(i + 1, len(ps)):
                if v[ps[i]] == v[ps[j]]:
                    dup_pairs[(ps[i], ps[j])] += 1
    if dup_pairs:
        for (a, b), c in sorted(dup_pairs.items()):
            print(f"    档 {a:g} 与 {b:g} 逐位相同的组数：{c}/{len(byrep)}")
        print("    → 说明探针在该区间**饱和**，x 轴没有真正移动 y 轴；"
              "这些档不能当作独立观测。")
    else:
        print("    无重复格。")
    return cells, levels, seeds


def section_continuous(cells, levels, seeds):
    print("\n" + "=" * 72)
    print("二、连续序参量 sparse.dwf（有界、无奇点）")
    print("=" * 72)
    print(f"{'p':>7} {'n':>5} {'mean':>8} {'sd':>7} {'median':>8} {'min':>7} {'max':>7}")
    for p in levels:
        v = [u["c4pp"]["sparse"]["dwf"] for s in seeds for u in cells[(s, p)]]
        v = [x for x in v if fin(x)]
        print(f"{p:>7g} {len(v):>5} {st.mean(v):>+8.4f} {st.stdev(v):>7.4f} "
              f"{st.median(v):>+8.4f} {min(v):>+7.3f} {max(v):>+7.3f}")

    print("\n逐籽格均值")
    print("seed   " + "".join(f"{'p='+format(p,'g'):>10}" for p in levels))
    for s in seeds:
        row = []
        for p in levels:
            v = [u["c4pp"]["sparse"]["dwf"] for u in cells[(s, p)]]
            v = [x for x in v if fin(x)]
            row.append(f"{st.mean(v):>+10.4f}" if v else f"{'-':>10}")
        print(f"{s:<6d} " + "".join(row))

    print("\n配对差 vs p=0（同籽配对，消掉籽间方差）")
    def cm(s, p):
        v = [u["c4pp"]["sparse"]["dwf"] for u in cells[(s, p)]]
        v = [x for x in v if fin(x)]
        return st.mean(v) if v else None
    for p in levels[1:]:
        d = [cm(s, p) - cm(s, 0.0) for s in seeds
             if cm(s, p) is not None and cm(s, 0.0) is not None]
        if len(d) < 3:
            print(f"    p={p:g}: n={len(d)} 不足，跳过")
            continue
        m = st.mean(d); sd = st.stdev(d); se = sd / math.sqrt(len(d))
        t = 2.365 if len(d) == 8 else 2.447
        star = "  ← 跨 0" if (m - t * se) < 0 < (m + t * se) else "  ← 不含 0"
        print(f"    p={p:<6g} Δ={m:+.4f} sd={sd:.4f} n={len(d)} "
              f"95%CI=[{m-t*se:+.3f},{m+t*se:+.3f}]{star}")


def section_binary(cells, levels, seeds, cut=0.5):
    print("\n" + "=" * 72)
    print(f"三、二值序参量：每次 run 是否「寄存器存活」（sparse.dwf > {cut}）")
    print("=" * 72)
    print(f"{'p':>7} {'存活':>7} {'比例':>7} {'Wilson 95%CI':>22}")
    for p in levels:
        v = [u["c4pp"]["sparse"]["dwf"] for s in seeds for u in cells[(s, p)]]
        v = [x for x in v if fin(x)]
        k = sum(1 for x in v if x > cut)
        lo, hi = wilson(k, len(v))
        print(f"{p:>7g} {k:>4}/{len(v):<3} {k/len(v):>7.3f}    [{lo:.3f}, {hi:.3f}]")

    print("\n判活线敏感性（若分布双峰，计数应对 cut 不敏感）")
    cuts = (0.3, 0.4, 0.5, 0.6)
    print(f"{'p':>7} " + "".join(f"{'>'+format(c,'g'):>9}" for c in cuts))
    for p in levels:
        v = [u["c4pp"]["sparse"]["dwf"] for s in seeds for u in cells[(s, p)]]
        v = [x for x in v if fin(x)]
        print(f"{p:>7g} " + "".join(f"{sum(1 for x in v if x > c):>9d}" for c in cuts))

    print("\n同籽内的分裂（双稳的直接证据：同籽不同重复落在不同簇）")
    for p in levels:
        full = part = zero = 0
        for s in seeds:
            v = [u["c4pp"]["sparse"]["dwf"] for u in cells[(s, p)]]
            v = [x for x in v if fin(x)]
            k = sum(1 for x in v if x > cut)
            if k == len(v) and v:
                full += 1
            elif k == 0:
                zero += 1
            else:
                part += 1
        if part:
            print(f"    p={p:<6g} 全存活籽={full}  部分存活={part}  全崩籽={zero}"
                  f"   ← 该档存在籽内双稳")
        else:
            print(f"    p={p:<6g} 全存活籽={full}  部分存活={part}  全崩籽={zero}")


def section_refuse_bic(cells, levels, seeds):
    print("\n" + "=" * 72)
    print("四、为什么这里**不做** M0/M1/M2 的 BIC 竞争")
    print("=" * 72)
    valid = []
    for p in levels:
        n_ok = sum(1 for s in seeds if any(
            fin(u["derived"].get("q")) for u in cells[(s, p)]))
        valid.append((p, n_ok))
    print("  q 的可用档位：" + "  ".join(f"p={p:g}:{k}/8籽" for p, k in valid))
    print("  1) p=1.0 全灭 → 该档零信息；0.25 有一半 NaN 且缺失非随机")
    print("  2) 有效 x 档 ≤4 个；二次模型对 3 个 x 精确插值（RSS=0），")
    print("     「M2 胜」是结构性的，不是经验证据")
    print("  3) 5 次重复被当成 5 个独立样本（伪重复）→ n 虚高 5 倍")
    print("  4) 预注册要求 ΔBIC≥10；报告在 ΔBIC=0.52 时宣布胜者，判据未执行")
    print("  → 结论：形状判定在本数据上**不可识别**，不报胜者。")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", required=True, help="sweep 的 results 目录")
    ap.add_argument("--tag", default="sweep")
    ap.add_argument("--cut", type=float, default=0.5)
    a = ap.parse_args()
    units = load_units(a.results, a.tag)
    if not units:
        print(f"没有找到 unit_{a.tag}*.json in {a.results}")
        return
    cells, levels, seeds = section_data_health(units)
    section_continuous(cells, levels, seeds)
    section_binary(cells, levels, seeds, a.cut)
    section_refuse_bic(cells, levels, seeds)
    print("\n" + "=" * 72)
    print("读法上限")
    print("=" * 72)
    print("  · 这是**剂量–反应曲线**，不是临界点测量；无关联长度、无簇结构")
    print("  · 禁止写 p_c、禁止写「测到临界」、禁止写「涌现→智能定律」")
    print("  · 换序参量属事后决定 → 本结果为**探索性**，不继承原预注册的确认性")
    print("  · 不改变 E2/E2b 的既有判决；S3 仍 CLOSED")


if __name__ == "__main__":
    main()
