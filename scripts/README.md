# scripts

`void_prescreen.py` is the read-only leak/VOID group-gate pre-screen (checklist V1–V7 in `docs/P2_void_prescreen_2026-10-30.md`).

```bash
python scripts/void_prescreen.py
python scripts/void_prescreen.py --summary path/to/summary.json
python scripts/void_prescreen.py --self-test
```

JSON goes to stdout. `--out` also writes that JSON, and refuses `frozen/` and `results/summary_*.json`.

中文：只读预筛。`frozen/` 与 `results/summary_*.json` 保持原样，科学臂保持关闭，VOID 线保持 0.35，分母保持 8。`unknown` 不计为 `no`。没有阳性对照时标记 `PROBE_UNCALIBRATED`。`scripts/fixtures/` 里的 JSON 都是合成夹具，不是科学跑。
