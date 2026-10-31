# Paper status

**Author:** 李逾凡 (Li Yufan)

**Topic:** non-creationism goal-bearing / SDIA necessity reconstruction (toy line: S1f2 → Dx2 → S1g → S1h2).

## Status (as of 2026-10-11, Asia/Shanghai)

- This repository is a **slim public reproduction package** of frozen thresholds, clean seeds, summary JSONs, and core toy code.
- Experiments were **internally preregistered** (thresholds frozen + sha256 before science runs).
- **Not peer-reviewed.** No journal submission status is claimed here.
- Results in `results/` are archival summaries from the closed internal runs; they are not a substitute for independent re-execution under the frozen protocols.

## What is / is not claimed

Allowed (with budget/architecture scope):

- L2-self on the toy lands in the **gated architecture (GRU)** bin after S1g (GRU A2C 8/8; RNN 0/8 untuned).
- After S1h2 selection fix, repaired ES is a **valid ruler** (easy 8/8); main 4/8 → **under matched budget, evolution did not reach**.
- BPTT credit assignment vs evolution axis receives **clean support at this budget**.

Forbidden overclaims (see also README and `docs/权威进度表_2026-10-10.md`):

- Do **not** write “evolution unreachable” (no budget scan).
- Do **not** write “prior-free / RNN unreachable in principle” (RNN untuned).
- Do **not** weaken leak VOID line **0.35** or shrink VOID denominator from **8**.
- Do **not** ship or require gene dumps for the public claim surface.
- **禁写数值 p_c 平移** / **Do not transfer a numeric lattice percolation \(p_c\)**: do not claim this protocol’s gating threshold is “≈ 2D site \(p_c\)≈0.5927 / bond 0.5 / 3D 0.3116”, and do not call E2’s 1/8, or the draft figure E2b 3/8, a measured \(p_c\). E2b’s 3/8 is from the 2026-10-30 draft; this package has **no** E2b archive and has **not** verified that count. Percolation here is only a **critical-skeleton analogy** (order parameter / connectivity threshold / diverging correlation length). Lattice, neighborhood, and occupation are not isomorphic; skeleton analogy ≠ numeric isomorphism. Allowed ceiling: a **falsifiable hypothesis** that effective occupation crossing a threshold yields register-like hold — not a measured result.
- **Do not read cross-seed scatter as a phase diagram**: E2’s eight-seed `every.dwf/sparse.dwf` span ≈ 0.44–1.01 (n=8, 95% CI half-width 0.175) is **seed noise**, not a scanned occupation axis. Do not estimate a critical point from it. An occupation sweep needs its own preregistration; these notes are not that preregistration.
- **`q` is cancelled.** The 2026-10-31 external occupation-sweep readout does not rehabilitate \(q = 1 - \mathrm{every}/\mathrm{sparse}\) (singularity, non-random missingness, low-\(p\) saturation; delivered ΔBIC below a ≥10 bar).
- **`sparse.dwf` is exploratory** (chosen after seeing the data). It is not a confirmatory order parameter and **does not claim a percolation \(p_c\)**.
- **S3 remains CLOSED.** These notes authorize **no new science runs**, do not change `results/` or `frozen/`, and do not reopen E2 or any other closed arm.

> Reading ceiling (2026-10-30): C4″ “directional 8/8 ∧ specific 3/8”, restated from the E2 archive in `docs/E2_C4pp_archive_extract_2026-10-30.md`, may be a **candidate** near-critical bottleneck reading. It is **not** a \(p_c\) measurement and **not** a theorem.

## Documentation addendum (2026-10-31)

Archival notes only. They do not move the 2026-10-11 claim surface above.

| File | What it is |
|------|------------|
| `docs/E2_C4pp_archive_extract_2026-10-30.md` | Restatement of the E2 archive (C4″ and leak). Not a phase diagram and not a \(p_c\). |
| `docs/P2_void_prescreen_2026-10-30.md` | P2 VOID/leak prescreen is **not identifiable** on that archive (leak pinned at chance, zero variance). |
| `docs/PROBE_AUDIT_leak_2026-10-30.md` | E2 leak-probe features are structurally zero, so VOID 0/8 is an idle instrument, not “no leak”. E2’s 1/8 gate is unchanged. |
| `docs/P1_occupation_sweep_READOUT_2026-10-31.md` | External sweep readout. **`q` cancelled.** **`sparse.dwf` exploratory.** Not a percolation \(p_c\). **S3 CLOSED.** |
| `tools/analyze_v2.py` | Readout script for that external dump. It does not train and it does not estimate \(p_c\). |

## Citation stub

```bibtex
@misc{li2026sdia_goal_bearing_repro,
  author       = {Li, Yufan and 李逾凡},
  title        = {SDIA Goal-Bearing Toy Repro (S1g / Dx2 / S1h2)},
  year         = {2026},
  howpublished = {GitHub repository},
  note         = {Internal preregistration; not peer-reviewed. MIT License.},
  url          = {https://github.com/theblackboxcat/sdia-goal-bearing-repro}
}
```
