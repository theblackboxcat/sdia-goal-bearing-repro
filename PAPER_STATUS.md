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
