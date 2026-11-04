#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Read-only leak/VOID group-gate pre-screen (checklist V1–V7).

The checklist lives in ``docs/P2_void_prescreen_2026-10-30.md``.
Each item is ``yes``, ``no``, or ``unknown``. ``unknown`` is never
counted as ``no``.

This tool only reads repository artifacts and an optional user-supplied
JSON summary. It does not modify ``frozen/`` or ``results/``, does not
train, does not open science arms, and does not authorize a run.
VOID line stays 0.35 (N=4, mean > 0.35). Denominator stays 8.
A missing positive control is tagged ``PROBE_UNCALIBRATED``.
A chance value pinned with zero variance is not a measurement and is
not read as no-leak. No numeric percolation p_c is claimed. S3 stays
CLOSED.

Usage (from the package root):
  python scripts/void_prescreen.py
  python scripts/void_prescreen.py --summary path/to/summary.json
  python scripts/void_prescreen.py --self-test
  python scripts/void_prescreen.py --out /tmp/void_prescreen.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

VOID_LINE = 0.35
DENOMINATOR = 8
TUNE_SEEDS = (100, 101, 102, 103)
# N=4 chance tied to the frozen 0.35 line. N=2 chance is the E2 archive
# pattern. Neither value is a percolation threshold.
CHANCE_N4 = 0.25
CHANCE_LEVELS = (CHANCE_N4, 0.5)

ROOT = Path(__file__).resolve().parent.parent
FROZEN = ROOT / "frozen"
RESULTS = ROOT / "results"
DOCS = ROOT / "docs"
FIXTURES = Path(__file__).resolve().parent / "fixtures"

CHECKLIST_DOC = DOCS / "P2_void_prescreen_2026-10-30.md"
PROBE_AUDIT_DOC = DOCS / "PROBE_AUDIT_leak_2026-10-30.md"
E2_EXTRACT_DOC = DOCS / "E2_C4pp_archive_extract_2026-10-30.md"

VERDICT_ZH = {"yes": "是", "no": "否", "unknown": "未知"}

ITEMS = (
    (
        "V1",
        "leak 探针阳性对照已跑，且注入档位单调报警",
        "Leak-probe positive control has been run, and injection levels alarm monotonically.",
        "否 → VOID 结果不得解释为无缺陷，只标 PROBE_UNCALIBRATED",
    ),
    (
        "V2",
        "干净样例 leak 报警数 = 0",
        "Clean-sample leak alarm count is 0.",
        "否 → 先修探针，不跑科学籽",
    ),
    (
        "V3",
        "VOID 线数值与来源（N 值／chance／A_emp）在预注册里写明且未改",
        "VOID line value and source (N / chance / A_emp) are written in the preregistration and unchanged.",
        "否 → PROTOCOL_VIOLATION",
    ),
    (
        "V4",
        "分母在预注册写明，且跑后未缩",
        "Denominator is written in the preregistration and was not shrunk after the run.",
        "否 → INVALID，不重算",
    ),
    (
        "V5",
        "科学籽与 tune 籽不重叠（Dx2 clean list vs 100–103）",
        "Science seeds do not overlap tune seeds (Dx2 clean list vs 100–103).",
        "否 → PROTOCOL_VIOLATION",
    ),
    (
        "V6",
        "缺陷轴（若作自变量）是制造的，不是放宽的",
        "If a defect axis is the independent variable, it is manufactured, not a relaxed line.",
        "否 → 拒跑",
    ),
    (
        "V7",
        "报告首页有 VOID 率与分母并列，且未把 VOID 计为 FAIL",
        "Report front page shows VOID rate beside the denominator, and does not count VOID as FAIL.",
        "否 → 报告退回",
    ),
)


class OutPathRefused(Exception):
    """Refused to write onto frozen science artifacts."""


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 16), b""):
            digest.update(chunk)
    return digest.hexdigest()


def snapshot_tree(directory: Path) -> dict:
    """Content hashes of every file under ``directory`` (read-only)."""
    found = {}
    if not directory.is_dir():
        return found
    for path in sorted(directory.rglob("*")):
        if path.is_file():
            found[str(path.relative_to(directory))] = file_sha256(path)
    return found


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def sidecar_hash(path: Path):
    sidecar = path.with_suffix(".sha256")
    if not sidecar.is_file():
        return None, sidecar
    token = sidecar.read_text(encoding="utf-8").split()[0]
    return token, sidecar


def is_num(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def near(left, right, eps: float = 1e-9) -> bool:
    return is_num(left) and is_num(right) and abs(float(left) - float(right)) <= eps


def make_check(check_id: str, token: str, evidence: list) -> dict:
    spec = {row[0]: row for row in ITEMS}[check_id]
    return {
        "id": check_id,
        "item_zh": spec[1],
        "item_en": spec[2],
        "disposition_if_no": spec[3],
        "verdict": token,
        "verdict_zh": VERDICT_ZH[token],
        "unknown_is_not_no": True,
        "evidence": list(evidence),
    }


def load_frozen_documents() -> dict:
    """Read every frozen JSON and its sidecar. Never writes."""
    documents = []
    if FROZEN.is_dir():
        for path in sorted(FROZEN.glob("*.json")):
            recorded, sidecar = sidecar_hash(path)
            actual = file_sha256(path)
            documents.append(
                {
                    "path": str(path.relative_to(ROOT)),
                    "data": load_json(path),
                    "sha256": actual,
                    "sidecar": str(sidecar.relative_to(ROOT)),
                    "sidecar_sha256": recorded,
                    "sidecar_match": recorded == actual,
                }
            )
    clean, thresholds = [], []
    for doc in documents:
        name = Path(doc["path"]).name
        if name.startswith("clean_seeds") or doc["data"].get("schema", "").startswith("clean_seeds"):
            clean.append(doc)
        else:
            thresholds.append(doc)
    return {"all": documents, "clean": clean, "thresholds": thresholds}


def load_result_summaries() -> list:
    found = []
    if not RESULTS.is_dir():
        return found
    for path in sorted(RESULTS.glob("summary_*.json")):
        found.append({"path": str(path.relative_to(ROOT)), "data": load_json(path)})
    return found


def doc_contains(path: Path, needle: str) -> bool:
    if not path.is_file():
        return False
    return needle in path.read_text(encoding="utf-8")


def n2_void_disabled_arms(thresholds: list) -> list:
    names = set()
    for doc in thresholds:
        arms = doc["data"].get("arms") or {}
        if not isinstance(arms, dict):
            continue
        for name, arm in arms.items():
            if not isinstance(arm, dict):
                continue
            acc = arm.get("acceptance_N2")
            if isinstance(acc, dict) and acc.get("C2_leak_void_enabled") is False:
                names.add(str(name))
    return sorted(names)


def science_tune_pairs(bundle: dict) -> list:
    """(label, science seeds, tune seeds) drawn from frozen files."""
    pairs = []
    for doc in bundle["clean"]:
        seeds = doc["data"].get("seeds")
        if isinstance(seeds, list):
            pairs.append((doc["path"], [int(s) for s in seeds], list(TUNE_SEEDS)))
    for doc in bundle["thresholds"]:
        seeds = doc["data"].get("seeds")
        tune = doc["data"].get("tune_seeds")
        if isinstance(seeds, list) and isinstance(tune, list):
            pairs.append(
                (doc["path"], [int(s) for s in seeds], [int(s) for s in tune])
            )
    return pairs


def collect_n4_line_facts(bundle: dict, summaries: list) -> tuple[list, list]:
    """Return (evidence strings, problems). A problem fails V3."""
    evidence = []
    problems = []
    for doc in bundle["all"]:
        if doc["sidecar_sha256"] is None:
            problems.append(f"{doc['path']} has no .sha256 sidecar")
        elif not doc["sidecar_match"]:
            problems.append(
                f"{doc['path']} sha256 {doc['sha256']} != sidecar {doc['sidecar_sha256']}"
            )
        else:
            evidence.append(f"{doc['path']} sha256 matches {doc['sidecar']}")

    for doc in bundle["thresholds"]:
        data = doc["data"]
        acc = data.get("acceptance_per_seed") or {}
        if "C2_leak_max_N4" in acc:
            value = acc["C2_leak_max_N4"]
            evidence.append(f"{doc['path']} acceptance_per_seed.C2_leak_max_N4={value}")
            if not near(value, VOID_LINE):
                problems.append(f"{doc['path']} C2_leak_max_N4={value} (expected {VOID_LINE})")
        if "C2_chance_N4" in acc:
            chance = acc["C2_chance_N4"]
            evidence.append(f"{doc['path']} C2_chance_N4={chance}")
            if not near(chance, CHANCE_N4):
                problems.append(f"{doc['path']} C2_chance_N4={chance} (expected {CHANCE_N4})")
        probe = data.get("leak_probe") or {}
        if isinstance(probe, dict) and "void_if_mean_gt" in probe:
            value = probe["void_if_mean_gt"]
            source = probe.get("source", "source field absent")
            evidence.append(
                f"{doc['path']} leak_probe.void_if_mean_gt={value}; source={source}"
            )
            if not near(value, VOID_LINE):
                problems.append(f"{doc['path']} void_if_mean_gt={value}")
        rules = data.get("void_rules") or {}
        if isinstance(rules, dict) and "forbid_weaken_leak_line" in rules:
            flag = rules["forbid_weaken_leak_line"]
            evidence.append(f"{doc['path']} void_rules.forbid_weaken_leak_line={flag}")
            if flag is not True:
                problems.append(f"{doc['path']} forbid_weaken_leak_line is not true")
        # N=2 easy rulers disable leak-VOID. That is not the N=4 line.
        arms = data.get("arms") or {}
        if isinstance(arms, dict):
            for name, arm in arms.items():
                if not isinstance(arm, dict):
                    continue
                acc_n2 = arm.get("acceptance_N2")
                if isinstance(acc_n2, dict) and "C2_leak_max" in acc_n2:
                    evidence.append(
                        f"{doc['path']} arm {name} N=2 C2_leak_max={acc_n2.get('C2_leak_max')} "
                        f"C2_leak_void_enabled={acc_n2.get('C2_leak_void_enabled')} "
                        "(not the N=4 VOID line; 0.35 is not applied and not weakened)"
                    )

    for doc in bundle["clean"]:
        protocol = doc["data"].get("protocol") or {}
        line = protocol.get("void_line_unchanged")
        evidence.append(
            f"{doc['path']} protocol.void_line_unchanged={line} "
            f"denom_unchanged={protocol.get('denom_unchanged')} "
            f"accept_leak_mean_max={protocol.get('accept_leak_mean_max')} "
            "(accept_leak_mean_max is the clean-list margin, not a second VOID line)"
        )
        if "void_line_unchanged" in protocol and not near(line, VOID_LINE):
            problems.append(f"{doc['path']} void_line_unchanged={line}")

    for summary in summaries:
        if Path(summary["path"]).name != "summary_Dx2.json":
            continue
        data = summary["data"]
        protocol = data.get("protocol") or {}
        meta = data.get("meta") or {}
        evidence.append(
            f"{summary['path']} protocol.void_line_unchanged={protocol.get('void_line_unchanged')} "
            f"meta.leak_max={meta.get('leak_max')} (read-only)"
        )
        if "void_line_unchanged" in protocol and not near(protocol["void_line_unchanged"], VOID_LINE):
            problems.append(f"{summary['path']} void_line_unchanged changed")
        if "leak_max" in meta and not near(meta["leak_max"], VOID_LINE):
            problems.append(f"{summary['path']} meta.leak_max changed")
    return evidence, problems


def collect_denom_facts(bundle: dict, summaries: list) -> tuple[list, list]:
    evidence = []
    problems = []
    for doc in bundle["clean"]:
        data = doc["data"]
        protocol = data.get("protocol") or {}
        n_field = data.get("n")
        n_list = len(data.get("seeds") or [])
        evidence.append(
            f"{doc['path']} n={n_field} len(seeds)={n_list} "
            f"denom_unchanged={protocol.get('denom_unchanged')}"
        )
        if not doc["sidecar_match"]:
            problems.append(f"{doc['path']} sidecar mismatch; cannot treat denominator as unchanged")
        if n_field is not None and int(n_field) != DENOMINATOR:
            problems.append(f"{doc['path']} n={n_field}")
        if n_list != DENOMINATOR:
            problems.append(f"{doc['path']} len(seeds)={n_list}")
        if "denom_unchanged" in protocol and int(protocol["denom_unchanged"]) != DENOMINATOR:
            problems.append(f"{doc['path']} denom_unchanged={protocol['denom_unchanged']}")

    for doc in bundle["thresholds"]:
        data = doc["data"]
        rules = data.get("void_rules") or {}
        evidence.append(
            f"{doc['path']} group_pass_of={data.get('group_pass_of')} "
            f"group_pass_min_seeds={data.get('group_pass_min_seeds')} "
            f"void_rules.denom_always={rules.get('denom_always') if isinstance(rules, dict) else None} "
            f"forbid_shrink_denom={rules.get('forbid_shrink_denom') if isinstance(rules, dict) else None}"
        )
        if not doc["sidecar_match"]:
            problems.append(f"{doc['path']} sidecar mismatch")
        if "group_pass_of" in data and int(data["group_pass_of"]) != DENOMINATOR:
            problems.append(f"{doc['path']} group_pass_of={data['group_pass_of']}")
        if isinstance(rules, dict) and "denom_always" in rules and int(rules["denom_always"]) != DENOMINATOR:
            problems.append(f"{doc['path']} denom_always={rules['denom_always']}")
        if isinstance(rules, dict) and rules.get("forbid_shrink_denom") is False:
            problems.append(f"{doc['path']} forbid_shrink_denom is false")
        seeds = data.get("seeds")
        if isinstance(seeds, list) and len(seeds) != DENOMINATOR:
            problems.append(f"{doc['path']} len(seeds)={len(seeds)}")

    for summary in summaries:
        data = summary["data"]
        if "denominator" in data and int(data["denominator"]) != DENOMINATOR:
            problems.append(f"{summary['path']} denominator={data['denominator']}")
        elif "denominator" in data:
            evidence.append(f"{summary['path']} denominator={data['denominator']}")
        protocol = data.get("protocol") or {}
        if "denom_unchanged" in protocol:
            evidence.append(f"{summary['path']} protocol.denom_unchanged={protocol['denom_unchanged']}")
            if int(protocol["denom_unchanged"]) != DENOMINATOR:
                problems.append(f"{summary['path']} denom_unchanged={protocol['denom_unchanged']}")
        arms = data.get("arms")
        if isinstance(arms, dict):
            for name, arm in arms.items():
                if isinstance(arm, dict) and "n" in arm and int(arm["n"]) != DENOMINATOR:
                    problems.append(f"{summary['path']} arm {name} n={arm['n']}")
        science = data.get("science")
        if isinstance(science, dict):
            for name, arm in science.items():
                if isinstance(arm, dict) and "n" in arm and int(arm["n"]) != DENOMINATOR:
                    problems.append(f"{summary['path']} science {name} n={arm['n']}")
            evidence.append(
                f"{summary['path']} science arm n fields checked against {DENOMINATOR}"
            )
    return evidence, problems


def overlap_problems(pairs: list) -> tuple[list, list]:
    evidence = []
    problems = []
    if not pairs:
        problems.append("no frozen science/tune seed lists found")
        return evidence, problems
    for label, science, tune in pairs:
        both = sorted(set(science) & set(tune))
        evidence.append(f"{label}: science {science} ∩ tune {tune} = {both or 'empty'}")
        if both:
            problems.append(f"{label} overlap {both}")
    return evidence, problems


def frozen_clean_flag_note(bundle: dict) -> dict:
    """Restate void_if_mean flags already stored on the clean-seed file."""
    flags = {"n_true": 0, "n_false": 0, "n_other": 0}
    for doc in bundle["clean"]:
        stats = doc["data"].get("per_seed_stats") or {}
        if not isinstance(stats, dict):
            continue
        for row in stats.values():
            if not isinstance(row, dict) or "void_if_mean" not in row:
                continue
            if row["void_if_mean"] is True:
                flags["n_true"] += 1
            elif row["void_if_mean"] is False:
                flags["n_false"] += 1
            else:
                flags["n_other"] += 1
    flags["note"] = (
        "Counts of void_if_mean already stored in frozen clean-seed JSON. "
        "Not a new measurement, not a positive control, and not an E2 reading."
    )
    return flags


def repo_archive_notes() -> dict:
    audit_present = PROBE_AUDIT_DOC.is_file()
    extract_present = E2_EXTRACT_DOC.is_file()
    checklist_present = CHECKLIST_DOC.is_file()
    # Presence checks only. 0.6 is the archive's N=2 line, restated so this
    # script can show it is not applied. It is not a measured p_c.
    e2_line_mentioned = doc_contains(E2_EXTRACT_DOC, "0.6") and doc_contains(
        E2_EXTRACT_DOC, "dx2_heritage_line_N4"
    )
    return {
        "checklist_doc": str(CHECKLIST_DOC.relative_to(ROOT)) if checklist_present else None,
        "probe_audit_doc": str(PROBE_AUDIT_DOC.relative_to(ROOT)) if audit_present else None,
        "e2_extract_doc": str(E2_EXTRACT_DOC.relative_to(ROOT)) if extract_present else None,
        "e2_probe": (
            "Archive states the E2 leak probe is uncalibrated (feature matrix "
            "structurally zero; VOID 0/8 is an idle instrument). This script does "
            "not rerun that probe and does not read that archive as no-leak."
        ),
        "archive_tags": ["PROBE_UNCALIBRATED"] if audit_present else [],
        "e2_void_line_archive_only": {
            "documented_applied_line": 0.6 if e2_line_mentioned else None,
            "documented_source": "A_empirical+0.10; N=2; chance=0.5",
            "heritage_n4_line": VOID_LINE,
            "applied_by_this_script": False,
            "weakens_0_35": False,
            "numeric_percolation_pc": False,
            "present_in_extract": e2_line_mentioned,
            "note": (
                "thresholds_E2.json is not in this package. The 0.6 figure is a "
                "restatement of the extract, not a line this script classifies with."
            ),
        },
        "s3": "CLOSED",
        "new_science_runs": "not_authorized",
    }


def positive_control_block(summary: dict | None):
    if not isinstance(summary, dict):
        return None
    for key in ("positive_control", "probe_positive_control"):
        if key in summary:
            return summary[key]
    return None


def as_alarm(value) -> bool:
    if isinstance(value, bool):
        return value
    if is_num(value):
        return float(value) > 0
    raise TypeError("alarm value must be bool or number")


def judge_monotonic(levels, alarms) -> tuple[bool, str]:
    if not isinstance(levels, (list, tuple)) or not isinstance(alarms, (list, tuple)):
        return False, "injection_levels and alarm must be lists"
    if len(levels) != len(alarms) or len(levels) < 2:
        return False, "need at least two paired injection levels"
    try:
        pairs = sorted(
            ((float(level), as_alarm(alarm)) for level, alarm in zip(levels, alarms)),
            key=lambda item: item[0],
        )
    except (TypeError, ValueError) as exc:
        return False, f"injection series is not numeric ({exc})"
    flags = [flag for _, flag in pairs]
    if flags != sorted(flags):
        return False, "alarm is not non-decreasing in injection level"
    if not any(flags):
        return False, "injection series never alarms"
    if all(flags):
        return False, "alarm is flat across injection levels"
    if not any((not flags[i]) and flags[i + 1] for i in range(len(flags) - 1)):
        return False, "injection series has no quiet-to-alarm step"
    return True, "alarm rises monotonically across injection levels"


def judge_positive_control(block) -> tuple[str, str]:
    """Return ('yes'|'no'|'absent', reason)."""
    if block is None:
        return "absent", "no positive_control object in the summary"
    if not isinstance(block, dict):
        return "no", "positive_control is not an object"
    if block.get("ran") is False:
        return "no", "positive_control.ran is false"
    levels = block.get("injection_levels", block.get("levels"))
    alarms = block.get("alarm", block.get("alarms"))
    if levels is not None or alarms is not None:
        ok, reason = judge_monotonic(levels, alarms)
        return ("yes" if ok else "no"), reason
    if block.get("monotonic_alarm") is True or block.get("passed") is True:
        return "yes", "positive_control flag is true; injection series not included"
    if block.get("monotonic_alarm") is False or block.get("passed") is False:
        return "no", "positive_control flag is false"
    return "no", "positive_control object does not show a monotonic alarm"


def clean_alarm_count(summary: dict | None, block) -> tuple[str, str]:
    """Return ('yes'|'no'|'unknown', reason) for V2."""
    if not isinstance(summary, dict):
        return (
            "unknown",
            "No summary was supplied. Dx2 clean-seed leak means are science-seed "
            "records, not the P2-a clean-sample alarm count.",
        )
    if "clean_sample_alarm_count" in summary:
        count = summary["clean_sample_alarm_count"]
        if not is_num(count):
            return "no", "clean_sample_alarm_count is not a number"
        if float(count) == 0:
            return "yes", "clean_sample_alarm_count is 0"
        return "no", f"clean_sample_alarm_count is {count}"
    if isinstance(block, dict):
        levels = block.get("injection_levels", block.get("levels"))
        alarms = block.get("alarm", block.get("alarms"))
        if isinstance(levels, (list, tuple)) and isinstance(alarms, (list, tuple)) and len(levels) == len(alarms):
            quiet = []
            try:
                for level, alarm in zip(levels, alarms):
                    if float(level) == 0.0:
                        quiet.append(as_alarm(alarm))
            except (TypeError, ValueError):
                quiet = []
            if quiet:
                if any(quiet):
                    return "no", "injection level 0 alarms"
                return "yes", "injection level 0 does not alarm"
    return "unknown", "summary has no clean_sample_alarm_count"


def summary_seed_ids(summary: dict) -> list:
    ids = []
    for _arm, rows in iter_groups(summary):
        for row in rows:
            if "seed" in row:
                ids.append(row["seed"])
    declared = summary.get("science_seeds")
    if isinstance(declared, list) and declared:
        return [int(s) if is_num(s) or (isinstance(s, str) and s.isdigit()) else s for s in declared]
    return ids


def summary_tune_ids(summary: dict) -> list:
    tune = summary.get("tune_seeds")
    if isinstance(tune, list) and tune:
        return [int(s) for s in tune]
    return list(TUNE_SEEDS)


def judge_defect_axis(summary: dict | None) -> tuple[str, str]:
    if not isinstance(summary, dict) or "defect_axis" not in summary:
        return (
            "unknown",
            "No defect axis is under test. P2's phase diagram is not identifiable "
            "on the E2 archive. S3 stays CLOSED. This script does not open an arm.",
        )
    raw = summary.get("defect_axis")
    if raw in (None, False, "", "not_used", "absent", "none"):
        return "unknown", f"defect_axis={raw!r}; axis is not an independent variable"
    token = str(raw).strip().lower()
    line = summary.get("void_line", VOID_LINE)
    line_ok = near(line, VOID_LINE)
    if token in {"relaxed", "weaken", "weakened", "weaken_line", "lowered_line"}:
        return "no", f"defect_axis={raw!r} relaxes the line"
    if token in {"manufactured", "induced", "injected"}:
        if not line_ok:
            return "no", "defect axis is marked manufactured but void_line is not 0.35"
        return "yes", "defect axis is manufactured and the VOID line is still 0.35"
    return "unknown", f"defect_axis={raw!r} is not a known manufactured-or-relaxed token"


def rows_fold_void_into_fail(rows: list) -> bool:
    for row in rows:
        status = str(row.get("status") or "").upper()
        if row.get("void") is True and status == "FAIL":
            return True
    return False


def judge_report_front_page(summary: dict | None, groups: list) -> tuple[str, str]:
    if not isinstance(summary, dict):
        return (
            "unknown",
            "No report was submitted. Shipped summaries keep a void count separate "
            "from pass and state denominator 8; that is not a V7 pass for a new report.",
        )
    page = summary.get("report_front_page")
    if isinstance(page, dict):
        shown_rate = page.get("void_rate_shown")
        shown_denom = page.get("denominator_shown")
        counted = page.get("void_counted_as_fail")
        if counted is True:
            return "no", "report_front_page.void_counted_as_fail is true"
        if shown_rate is False or shown_denom is False:
            return "no", "report front page omits VOID rate or denominator"
        if shown_rate is True and shown_denom is True and counted is False:
            if any(rows_fold_void_into_fail(rows) for _arm, rows in groups):
                return "no", "a seed is status FAIL while void is true"
            return "yes", "report front page shows VOID rate and denominator; VOID is not FAIL"
        return "unknown", "report_front_page is incomplete"
    # Structural reading of a summary that already carries the two fields.
    has_denom = "denominator" in summary
    has_void = "void" in summary or "n_void" in summary
    arms = summary.get("arms") if isinstance(summary.get("arms"), dict) else {}
    science = summary.get("science") if isinstance(summary.get("science"), dict) else {}
    for arm in list(arms.values()) + list(science.values()):
        if isinstance(arm, dict):
            has_denom = has_denom or "n" in arm
            has_void = has_void or "void" in arm or "n_void" in arm
    if not has_denom and not has_void:
        return "unknown", "summary has no report front-page fields"
    if has_denom and has_void:
        if any(rows_fold_void_into_fail(rows) for _arm, rows in groups):
            return "no", "a seed is status FAIL while void is true"
        return "yes", "summary object carries denominator and void count as separate fields"
    return "no", "summary shows only one of VOID count and denominator"


def build_checks(bundle: dict, summaries: list, summary: dict | None, groups: list) -> list:
    archive = repo_archive_notes()
    v1_evidence = [
        "This package does not ship a leak-probe positive-control log or probe_v2.py.",
        archive["e2_probe"],
    ]
    if summary is None:
        v1 = "unknown"
        v1_evidence.append("Verdict unknown. Unknown is not no.")
    else:
        status, reason = judge_positive_control(positive_control_block(summary))
        if status == "absent":
            v1 = "unknown"
            v1_evidence.append(reason + ". Verdict stays unknown; classification is tagged PROBE_UNCALIBRATED.")
        elif status == "yes":
            v1 = "yes"
            v1_evidence.append(reason)
        else:
            v1 = "no"
            v1_evidence.append(reason)

    v2_token, v2_reason = clean_alarm_count(summary, positive_control_block(summary) if summary else None)
    if summary is None:
        v2_evidence = [v2_reason, "Verdict unknown. Unknown is not no."]
    else:
        v2_evidence = [v2_reason]

    line_evidence, line_problems = collect_n4_line_facts(bundle, summaries)
    line_evidence.append(
        "E2 extract applied line stays archive-only and is not the classification line."
    )
    if isinstance(summary, dict) and "void_line" in summary and not near(summary["void_line"], VOID_LINE):
        line_problems.append(
            f"summary declares void_line={summary['void_line']}; classification stays on {VOID_LINE}"
        )
    if isinstance(summary, dict) and summary.get("weaken_void_line") is True:
        line_problems.append("summary sets weaken_void_line true")
    v3 = "no" if line_problems else "yes"
    if line_problems:
        line_evidence.extend(f"PROBLEM: {item}" for item in line_problems)
    if not bundle["thresholds"] and not bundle["clean"]:
        v3 = "unknown"
        line_evidence.append("No frozen threshold or clean-seed file was found.")

    denom_evidence, denom_problems = collect_denom_facts(bundle, summaries)
    if isinstance(summary, dict):
        if "denominator" in summary and int(summary["denominator"]) != DENOMINATOR:
            denom_problems.append(
                f"summary denominator={summary['denominator']}; protocol denominator stays {DENOMINATOR}; rate not recomputed"
            )
        if "denominator_used" in summary and int(summary["denominator_used"]) != DENOMINATOR:
            denom_problems.append(f"summary denominator_used={summary['denominator_used']}")
        if summary.get("denom_shrunk") is True:
            denom_problems.append("summary denom_shrunk is true")
    v4 = "no" if denom_problems else "yes"
    if denom_problems:
        denom_evidence.extend(f"PROBLEM: {item}" for item in denom_problems)

    pairs = science_tune_pairs(bundle)
    overlap_evidence, overlap_bad = overlap_problems(pairs)
    if isinstance(summary, dict):
        science = summary_seed_ids(summary)
        tune = summary_tune_ids(summary)
        if science:
            both = sorted(set(science) & set(tune))
            overlap_evidence.append(f"summary science ∩ tune = {both or 'empty'}")
            if both:
                overlap_bad.append(f"summary overlap {both}")
            clean_ids = []
            for doc in bundle["clean"]:
                clean_ids.extend(int(s) for s in doc["data"].get("seeds") or [])
            if clean_ids and set(science) != set(clean_ids):
                overlap_evidence.append(
                    "summary science seeds are not the frozen Dx2 clean list; "
                    "V5 only requires non-overlap with tune seeds"
                )
    v5 = "no" if overlap_bad else ("yes" if pairs else "unknown")
    if overlap_bad:
        overlap_evidence.extend(f"PROBLEM: {item}" for item in overlap_bad)

    v6_token, v6_reason = judge_defect_axis(summary)
    v7_token, v7_reason = judge_report_front_page(summary, groups)

    return [
        make_check("V1", v1, v1_evidence),
        make_check("V2", v2_token, v2_evidence),
        make_check("V3", v3, line_evidence),
        make_check("V4", v4, denom_evidence),
        make_check("V5", v5, overlap_evidence),
        make_check("V6", v6_token, [v6_reason, "Unknown is not no."]),
        make_check("V7", v7_token, [v7_reason, "Unknown is not no."]),
    ]


def gate_of(checks: list) -> dict:
    counts = {"yes": 0, "no": 0, "unknown": 0}
    for check in checks:
        counts[check["verdict"]] += 1
    if counts["no"]:
        state = "blocked"
    elif counts["unknown"]:
        state = "not_cleared_unknown_remains"
    else:
        state = "checklist_all_yes"
    tags = []
    for check in checks:
        if check["verdict"] != "no":
            continue
        if check["id"] == "V1":
            tags.append("PROBE_UNCALIBRATED")
        elif check["id"] == "V2":
            tags.append("PROBE_CLEAN_SAMPLE_FAILED")
        elif check["id"] in {"V3", "V5"}:
            tags.append("PROTOCOL_VIOLATION")
        elif check["id"] == "V4":
            tags.append("INVALID")
        elif check["id"] == "V6":
            tags.append("REJECT_RUN")
        elif check["id"] == "V7":
            tags.append("REPORT_RETURNED")
    return {
        "state": state,
        "cleared": state == "checklist_all_yes",
        "unknown_counted_as_no": False,
        "authorizes_new_science_run": False,
        "s3": "CLOSED",
        "counts": counts,
        "tags": tags,
    }


def leak_fields(row: dict) -> tuple:
    leak = None
    if is_num(row.get("leak_mean")):
        leak = float(row["leak_mean"])
    elif is_num(row.get("leak")):
        leak = float(row["leak"])
    else:
        nested = row.get("C2_leak")
        if isinstance(nested, dict) and is_num(nested.get("mean")):
            leak = float(nested["mean"])
        elif is_num(nested):
            leak = float(nested)
    sd = None
    for key in ("sd", "leak_sd"):
        if is_num(row.get(key)):
            sd = float(row[key])
            break
    samples = None
    for key in ("samples", "leak_samples"):
        if isinstance(row.get(key), list):
            samples = row[key]
            break
    nested = row.get("C2_leak")
    if isinstance(nested, dict):
        if sd is None and is_num(nested.get("sd")):
            sd = float(nested["sd"])
        if samples is None and isinstance(nested.get("samples"), list):
            samples = nested["samples"]
    return leak, sd, samples


def input_status(row: dict) -> str:
    if isinstance(row.get("status"), str) and row["status"].strip():
        return row["status"].strip().upper()
    if row.get("void") is True:
        return "VOID"
    if row.get("pass") is True:
        return "PASS"
    if row.get("pass") is False:
        return "FAIL"
    return "UNSPECIFIED"


def normalize_rows(raw) -> list:
    rows = []
    if isinstance(raw, dict):
        items = raw.items()
    elif isinstance(raw, list):
        items = ((None, row) for row in raw)
    else:
        return rows
    for key, row in items:
        if not isinstance(row, dict):
            continue
        copied = dict(row)
        if "seed" not in copied and key is not None:
            copied["seed"] = int(key) if str(key).isdigit() else key
        leak, sd, samples = leak_fields(copied)
        copied["_leak_mean"] = leak
        copied["_sd"] = sd
        copied["_samples"] = samples
        copied["_status"] = input_status(copied)
        rows.append(copied)
    return rows


def iter_groups(summary: dict) -> list:
    groups = []
    if isinstance(summary.get("seeds"), list):
        groups.append((summary.get("arm"), normalize_rows(summary["seeds"])))
    if isinstance(summary.get("per_seed"), (list, dict)):
        groups.append((summary.get("arm"), normalize_rows(summary["per_seed"])))
    arms = summary.get("arms")
    if isinstance(arms, dict):
        for name, arm in arms.items():
            if isinstance(arm, dict) and "per_seed" in arm:
                groups.append((str(name), normalize_rows(arm["per_seed"])))
    science = summary.get("science")
    if isinstance(science, dict):
        for name, arm in science.items():
            if isinstance(arm, dict) and "per_seed" in arm:
                groups.append((str(name), normalize_rows(arm["per_seed"])))
    return groups


def chance_zero_variance(rows: list, declared_chance) -> bool:
    means = [row["_leak_mean"] for row in rows if row["_leak_mean"] is not None]
    if len(means) < 2:
        return False
    if any(abs(value - means[0]) > 1e-12 for value in means):
        return False
    saw = False
    for row in rows:
        if row["_leak_mean"] is None:
            continue
        if row["_sd"] is not None:
            saw = True
            if abs(row["_sd"]) > 1e-12:
                return False
        samples = row["_samples"]
        if isinstance(samples, list) and samples:
            saw = True
            try:
                first = float(samples[0])
            except (TypeError, ValueError):
                return False
            for sample in samples:
                try:
                    if abs(float(sample) - first) > 1e-12:
                        return False
                except (TypeError, ValueError):
                    return False
    if not saw:
        return False
    chances = set(CHANCE_LEVELS)
    if is_num(declared_chance):
        chances.add(float(declared_chance))
    return any(abs(means[0] - chance) <= 1e-9 for chance in chances)


def line_applies(arm, disabled_arms: list) -> bool:
    if arm is None:
        return True
    return str(arm) not in set(disabled_arms)


def classify_summary(summary: dict, disabled_arms: list, denom_ok: bool) -> dict:
    control, control_reason = judge_positive_control(positive_control_block(summary))
    declared_chance = summary.get("chance", summary.get("chance_theoretical"))
    tags = []
    if control != "yes":
        tags.append("PROBE_UNCALIBRATED")
    groups_out = []
    all_candidates = []
    status_counts = {"PASS": 0, "FAIL": 0, "VOID": 0, "UNSPECIFIED": 0, "OTHER": 0}
    any_withheld = False
    any_applied = False

    for arm, rows in iter_groups(summary):
        applied = line_applies(arm, disabled_arms)
        withheld = False
        group_tags = []
        classified = []
        candidates = []
        if not applied:
            group_tags.append("VOID_LINE_NOT_APPLIED")
            for row in rows:
                classified.append(
                    {
                        "arm": arm,
                        "seed": row.get("seed"),
                        "leak_mean": row["_leak_mean"],
                        "class": "void_line_not_applied",
                        "input_status": row["_status"],
                    }
                )
        elif chance_zero_variance(rows, declared_chance):
            withheld = True
            any_withheld = True
            group_tags.extend(["ZERO_VARIANCE_AT_CHANCE", "NOT_A_MEASUREMENT"])
            for row in rows:
                classified.append(
                    {
                        "arm": arm,
                        "seed": row.get("seed"),
                        "leak_mean": row["_leak_mean"],
                        "class": "not_a_measurement",
                        "input_status": row["_status"],
                        "above_line_if_forced": (
                            row["_leak_mean"] is not None and row["_leak_mean"] > VOID_LINE
                        ),
                    }
                )
        else:
            any_applied = True
            for row in rows:
                leak = row["_leak_mean"]
                if leak is None:
                    klass = "leak_mean_missing"
                elif leak > VOID_LINE:
                    klass = "VOID_CANDIDATE"
                    candidates.append(row.get("seed"))
                    all_candidates.append({"arm": arm, "seed": row.get("seed"), "leak_mean": leak})
                else:
                    klass = "below_void_line"
                classified.append(
                    {
                        "arm": arm,
                        "seed": row.get("seed"),
                        "leak_mean": leak,
                        "class": klass,
                        "input_status": row["_status"],
                    }
                )
        for row in rows:
            status = row["_status"]
            if status in status_counts:
                status_counts[status] += 1
            else:
                status_counts["OTHER"] += 1
        n_void = len(candidates)
        rate = None
        rate_reason = None
        if not applied:
            rate_reason = "N=2 easy arm keeps leak-VOID disabled in frozen thresholds; 0.35 was not applied and was not weakened"
        elif withheld:
            rate_reason = (
                "zero-variance chance pin is not a measurement; VOID rate withheld "
                "so it cannot be read as no-leak or as a new VOID count"
            )
        elif control != "yes":
            rate_reason = "positive control is not a pass; VOID rate withheld; raw candidate list is only a pre-screen flag"
        elif not denom_ok:
            rate_reason = "INVALID denominator; protocol denominator stays 8; rate not recomputed"
        elif len(rows) != DENOMINATOR:
            rate_reason = (
                f"listed {len(rows)} seeds; protocol denominator stays {DENOMINATOR}; "
                "rate not recomputed"
            )
        else:
            rate = {"numerator": n_void, "denominator": DENOMINATOR}
            rate_reason = "numerator is VOID candidates; denominator is the protocol 8"
        groups_out.append(
            {
                "arm": arm,
                "n_listed": len(rows),
                "line_applied": applied and not withheld,
                "void_calls_withheld": withheld or not applied,
                "n_void_candidates": n_void,
                "void_candidate_seeds": candidates,
                "n_below_line": sum(1 for item in classified if item["class"] == "below_void_line"),
                "n_missing_leak": sum(1 for item in classified if item["class"] == "leak_mean_missing"),
                "tags": group_tags,
                "void_rate": rate,
                "void_rate_reason": rate_reason,
                "seeds": classified,
            }
        )
        tags.extend(group_tags)

    # Stable unique tags.
    deduped = []
    for tag in tags:
        if tag not in deduped:
            deduped.append(tag)

    publish_rates = [
        group["void_rate"]
        for group in groups_out
        if group["void_rate"] is not None
    ]
    overall_rate = publish_rates[0] if len(publish_rates) == 1 else None
    if len(publish_rates) > 1:
        overall_rate = None
    return {
        "void_line": VOID_LINE,
        "rule": "leak_mean > 0.35",
        "denominator_protocol": DENOMINATOR,
        "positive_control": control,
        "positive_control_reason": control_reason,
        "tags": deduped,
        "interprets_as_no_leak": False,
        "below_line_is_not_no_leak": True,
        "authorizes_new_science_run": False,
        "numeric_percolation_pc_claimed": False,
        "s3": "CLOSED",
        "n_void_candidates": len(all_candidates),
        "void_candidate_seeds": all_candidates,
        "void_rate": overall_rate if not any_withheld else None,
        "void_rate_reason": (
            "withheld because at least one group is not a measurement"
            if any_withheld
            else ("published" if overall_rate else "not published")
        ),
        "input_status_counts": status_counts,
        "pass_count": status_counts["PASS"],
        "fail_count": status_counts["FAIL"],
        "void_status_count": status_counts["VOID"],
        "void_not_counted_as_fail": True,
        "rate_recomputed_on_shrunk_denominator": False,
        "groups": groups_out,
        "input_synthetic": bool(summary.get("synthetic")) if isinstance(summary, dict) else False,
        "measurement_groups": any_applied and not any_withheld,
    }


def boundaries() -> dict:
    return {
        "s3": "CLOSED",
        "new_science_runs": "not_authorized",
        "void_line": VOID_LINE,
        "void_rule": "leak_mean > 0.35",
        "denominator": DENOMINATOR,
        "numeric_percolation_pc_claimed": False,
        "e2_uncalibrated_probe": "not_reinterpreted_as_no_leak",
        "unknown_counted_as_no": False,
        "read_only": True,
    }


def build_report(summary: dict | None = None, summary_path: Path | None = None) -> dict:
    bundle = load_frozen_documents()
    summaries = load_result_summaries()
    groups = iter_groups(summary) if isinstance(summary, dict) else []
    checks = build_checks(bundle, summaries, summary, groups)
    denom_ok = next(check["verdict"] for check in checks if check["id"] == "V4") == "yes"
    classification = None
    if isinstance(summary, dict):
        classification = classify_summary(summary, n2_void_disabled_arms(bundle["thresholds"]), denom_ok)
    clean_seeds = []
    for doc in bundle["clean"]:
        clean_seeds.extend(int(s) for s in doc["data"].get("seeds") or [])
    return {
        "schema": "void_prescreen_report_v1",
        "mode": "summary" if summary is not None else "repo",
        "summary_path": str(summary_path) if summary_path else None,
        "boundaries": boundaries(),
        "checks": checks,
        "gate": gate_of(checks),
        "classification": classification,
        "loaded": {
            "clean_seeds": clean_seeds,
            "clean_seeds_n": len(clean_seeds),
            "tune_seeds": list(TUNE_SEEDS),
            "n2_leak_void_disabled_arms": n2_void_disabled_arms(bundle["thresholds"]),
            "frozen_files": [
                {
                    "path": doc["path"],
                    "sha256": doc["sha256"],
                    "sidecar_match": doc["sidecar_match"],
                }
                for doc in bundle["all"]
            ],
            "result_summaries_read": [item["path"] for item in summaries],
            "frozen_clean_void_if_mean_flags": frozen_clean_flag_note(bundle),
        },
        "archive_notes": repo_archive_notes(),
        "authorizes_new_science_run": False,
    }


def guard_out_path(path: Path) -> Path:
    resolved = path.expanduser().resolve()
    frozen = FROZEN.resolve()
    results = RESULTS.resolve()
    if resolved == frozen or frozen in resolved.parents:
        raise OutPathRefused(f"refusing to write inside {frozen}")
    if resolved.suffix == ".sha256":
        raise OutPathRefused("refusing to write a .sha256 file")
    if resolved.parent == results and resolved.name.startswith("summary_"):
        raise OutPathRefused(f"refusing to write {resolved}")
    if resolved == results:
        raise OutPathRefused(f"refusing to write {resolved}")
    return resolved


def emit_json(report: dict, out_path: Path | None) -> None:
    text = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if out_path is not None:
        resolved = guard_out_path(out_path)
        resolved.parent.mkdir(parents=True, exist_ok=True)
        resolved.write_text(text, encoding="utf-8")
    sys.stdout.write(text)


def emit_human(report: dict, stream) -> None:
    if report.get("schema") == "void_prescreen_self_test_v1":
        status = "PASS" if report.get("passed") else "FAIL"
        stream.write(f"self-test {status}  assertions={len(report.get('assertions', []))}\n")
        for item in report.get("assertions", []):
            mark = "ok" if item["passed"] else "FAIL"
            stream.write(f"  [{mark}] {item['name']}: {item['detail']}\n")
        return
    gate = report["gate"]
    counts = gate["counts"]
    stream.write(
        f"void_prescreen read-only  S3 CLOSED  void_line {VOID_LINE}  denom {DENOMINATOR}\n"
    )
    for check in report["checks"]:
        stream.write(f"  {check['id']}  {check['verdict']}\n")
    stream.write(
        f"counts yes={counts['yes']} no={counts['no']} unknown={counts['unknown']} "
        "(unknown is not counted as no)\n"
    )
    stream.write(
        f"gate {gate['state']}  authorizes_new_science_run false\n"
    )
    classification = report.get("classification")
    if classification:
        seeds = [item["seed"] for item in classification["void_candidate_seeds"]]
        stream.write(
            f"VOID candidates {seeds}  tags {classification['tags']}  "
            f"pass={classification['pass_count']} fail={classification['fail_count']} "
            f"void_status={classification['void_status_count']}\n"
        )
        stream.write("interprets_as_no_leak false\n")


def assert_that(results: list, name: str, condition: bool, detail: str) -> None:
    results.append({"name": name, "passed": bool(condition), "detail": detail})


def self_test() -> tuple[dict, int]:
    before = {"frozen": snapshot_tree(FROZEN), "results": snapshot_tree(RESULTS)}
    assertions = []
    fixture_reports = {}
    default = None
    try:
        default = build_report(None)
        by_id = {check["id"]: check["verdict"] for check in default["checks"]}
        assert_that(assertions, "default_v1_unknown", by_id.get("V1") == "unknown", by_id.get("V1"))
        assert_that(assertions, "default_v2_unknown", by_id.get("V2") == "unknown", by_id.get("V2"))
        assert_that(assertions, "default_v3_yes", by_id.get("V3") == "yes", by_id.get("V3"))
        assert_that(assertions, "default_v4_yes", by_id.get("V4") == "yes", by_id.get("V4"))
        assert_that(assertions, "default_v5_yes", by_id.get("V5") == "yes", by_id.get("V5"))
        assert_that(assertions, "default_v6_unknown", by_id.get("V6") == "unknown", by_id.get("V6"))
        assert_that(assertions, "default_v7_unknown", by_id.get("V7") == "unknown", by_id.get("V7"))
        assert_that(
            assertions,
            "unknown_not_counted_as_no",
            default["gate"]["unknown_counted_as_no"] is False
            and default["gate"]["counts"]["unknown"] == 4
            and default["gate"]["counts"]["no"] == 0,
            str(default["gate"]["counts"]),
        )
        assert_that(
            assertions,
            "protocol_constants",
            default["boundaries"]["void_line"] == 0.35
            and default["boundaries"]["denominator"] == 8
            and default["authorizes_new_science_run"] is False
            and default["boundaries"]["numeric_percolation_pc_claimed"] is False,
            "0.35 / 8 / no run / no p_c",
        )
        assert_that(
            assertions,
            "archive_e2_not_no_leak",
            "PROBE_UNCALIBRATED" in default["archive_notes"]["archive_tags"]
            and default["archive_notes"]["e2_void_line_archive_only"]["applied_by_this_script"] is False,
            "archive tag present; 0.6 not applied",
        )

        expected = {
            "high_leak.json": "high_leak",
            "clean_low_leak.json": "clean_low",
            "missing_positive_control.json": "missing_control",
            "chance_zero_variance.json": "chance_zero_variance",
            "shrunk_denominator.json": "shrunk_denominator",
        }
        for filename, label in expected.items():
            path = FIXTURES / filename
            payload = load_json(path)
            fixture_reports[label] = build_report(payload, path)

        high = fixture_reports["high_leak"]["classification"]
        high_seeds = [item["seed"] for item in high["void_candidate_seeds"]]
        assert_that(
            assertions,
            "high_leak_marks_void_candidate",
            high_seeds == [9001, 9002, 9003, 9007],
            str(high_seeds),
        )
        assert_that(
            assertions,
            "exact_line_not_void_candidate",
            9006 not in high_seeds and 9008 not in high_seeds and 9004 not in high_seeds,
            "0.35 and below stay off the candidate list",
        )
        assert_that(
            assertions,
            "high_leak_counts",
            high["pass_count"] == 4 and high["fail_count"] == 0 and high["void_status_count"] == 4,
            f"pass={high['pass_count']} fail={high['fail_count']} void={high['void_status_count']}",
        )
        assert_that(
            assertions,
            "high_leak_control_present",
            "PROBE_UNCALIBRATED" not in high["tags"] and high["void_rate"] == {"numerator": 4, "denominator": 8},
            str(high["tags"]),
        )

        low = fixture_reports["clean_low"]["classification"]
        assert_that(
            assertions,
            "clean_low_leak_not_void_candidate",
            low["n_void_candidates"] == 0 and low["void_candidate_seeds"] == [],
            f"n_void_candidates={low['n_void_candidates']}",
        )
        assert_that(
            assertions,
            "clean_low_not_phrased_as_no_leak",
            low["interprets_as_no_leak"] is False and low["below_line_is_not_no_leak"] is True,
            "interprets_as_no_leak false",
        )

        missing = fixture_reports["missing_control"]["classification"]
        assert_that(
            assertions,
            "missing_positive_control_tags_PROBE_UNCALIBRATED",
            "PROBE_UNCALIBRATED" in missing["tags"] and missing["void_rate"] is None,
            str(missing["tags"]),
        )
        missing_checks = {check["id"]: check["verdict"] for check in fixture_reports["missing_control"]["checks"]}
        assert_that(
            assertions,
            "missing_positive_control_v1_unknown_not_no",
            missing_checks["V1"] == "unknown" and missing["interprets_as_no_leak"] is False,
            missing_checks["V1"],
        )

        chance = fixture_reports["chance_zero_variance"]["classification"]
        assert_that(
            assertions,
            "chance_zero_variance_not_void_and_not_no_leak",
            chance["n_void_candidates"] == 0
            and chance["void_rate"] is None
            and "ZERO_VARIANCE_AT_CHANCE" in chance["tags"]
            and "PROBE_UNCALIBRATED" in chance["tags"]
            and chance["interprets_as_no_leak"] is False,
            str(chance["tags"]),
        )

        shrunk = fixture_reports["shrunk_denominator"]["classification"]
        shrunk_checks = {check["id"]: check["verdict"] for check in fixture_reports["shrunk_denominator"]["checks"]}
        assert_that(
            assertions,
            "shrunk_denominator_invalid_not_recomputed",
            shrunk_checks["V4"] == "no"
            and "INVALID" in fixture_reports["shrunk_denominator"]["gate"]["tags"]
            and shrunk["void_rate"] is None
            and shrunk["rate_recomputed_on_shrunk_denominator"] is False
            and [item["seed"] for item in shrunk["void_candidate_seeds"]] == [9043],
            f"V4={shrunk_checks['V4']} rate={shrunk['void_rate']}",
        )

        refused = []
        for bad in (
            FROZEN / "clean_seeds_Dx2.json",
            FROZEN / "not_a_real_file.sha256",
            RESULTS / "summary_Dx2.json",
        ):
            try:
                guard_out_path(bad)
            except OutPathRefused:
                refused.append(True)
            else:
                refused.append(False)
        assert_that(
            assertions,
            "refuses_writes_into_frozen_and_results",
            all(refused),
            f"refused={refused}",
        )
    except Exception as exc:
        assert_that(assertions, "self_test_exception", False, f"{type(exc).__name__}: {exc}")
    finally:
        after = {"frozen": snapshot_tree(FROZEN), "results": snapshot_tree(RESULTS)}
        assert_that(
            assertions,
            "frozen_and_results_unmodified",
            before == after,
            "content hashes unchanged" if before == after else "HASH CHANGED",
        )

    passed = all(item["passed"] for item in assertions)
    report = {
        "schema": "void_prescreen_self_test_v1",
        "passed": passed,
        "assertions": assertions,
        "default_checklist_verdicts": (
            {check["id"]: check["verdict"] for check in default["checks"]} if default else {}
        ),
        "fixtures": {
            label: {
                "n_void_candidates": item["classification"]["n_void_candidates"],
                "void_candidate_seeds": item["classification"]["void_candidate_seeds"],
                "tags": item["classification"]["tags"],
                "void_rate": item["classification"]["void_rate"],
                "pass_count": item["classification"]["pass_count"],
                "fail_count": item["classification"]["fail_count"],
                "void_status_count": item["classification"]["void_status_count"],
                "interprets_as_no_leak": item["classification"]["interprets_as_no_leak"],
                "gate": item["gate"]["state"],
            }
            for label, item in fixture_reports.items()
        },
        "boundaries": boundaries(),
        "authorizes_new_science_run": False,
    }
    return report, (0 if passed else 1)


def main(argv: list | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Read-only leak/VOID group-gate pre-screen (V1–V7). Does not modify frozen/ or open arms."
    )
    parser.add_argument(
        "--summary",
        type=Path,
        default=None,
        help="Optional seed-level JSON to classify. Read-only. Not written back.",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Also write the JSON report to this path. Refuses frozen/ and results/summary_*.json.",
    )
    parser.add_argument(
        "--self-test",
        action="store_true",
        help="Run synthetic fixtures under scripts/fixtures/ and a frozen/ mutation check.",
    )
    args = parser.parse_args(argv)
    if args.self_test and args.summary is not None:
        sys.stderr.write("use either --self-test or --summary\n")
        return 2
    try:
        if args.out is not None:
            guard_out_path(args.out)
        if args.self_test:
            report, code = self_test()
        elif args.summary is not None:
            if not args.summary.is_file():
                sys.stderr.write(f"summary not found: {args.summary}\n")
                return 2
            report = build_report(load_json(args.summary), args.summary)
            code = 0
        else:
            report = build_report(None)
            code = 0
        emit_json(report, args.out)
        emit_human(report, sys.stderr)
        return code
    except OutPathRefused as exc:
        sys.stderr.write(f"{exc}\n")
        return 2
    except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        sys.stderr.write(f"void_prescreen error: {exc}\n")
        return 2


if __name__ == "__main__":
    sys.exit(main())
