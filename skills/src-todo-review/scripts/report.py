#!/usr/bin/env python3
#
# SPDX-License-Identifier: BSD-2-Clause
#
"""Write the tracking spreadsheet from the ledger.

    report.py -l ledger.jsonl [-c commits.jsonl] -o review.xlsx --date D

Sheets: README, Summary (formulas over All items), Triage (one row per
reviewed item, with a status column to update by hand), By area
(formulas), Commits, Patches (the proposed patch of each FIX item), and
All items (every marker comment still in the tree).  Counts are COUNTIFS formulas, so filtering or correcting a row in
All items updates them; run the xlsx skill's recalc.py afterwards so the
cached values are filled in.  The Triage sheet also shows the severity,
category and cluster that the fix sorting agent gave each FIX and DESIGN
item (ledger.py merge -k sort), and sorts them by severity.
"""

import argparse
import json
from collections import Counter

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

FONT = "Arial"
HEAD_FILL = PatternFill("solid", fgColor="DDE4EE")
LABELS = ["STALE", "ACTIONABLE", "NOTE", "NOT_MARKER", "LOOK"]
VERDICTS = ["REMOVE", "REWORD", "FIX", "DESIGN", "KEEP", "NOT_MARKER", "UNSURE"]
TRACK = ["待處理", "已提交到分支", "已送審", "已併入上游", "不處理"]
SEVERITY = ["high", "medium", "low"]
UPSTREAM = "https://github.com/freebsd/freebsd-src/blob/%s/%s#L%d"

ALL_COLS = [  # header, key, width
    ("ID", "id", 15), ("狀態", "status", 11), ("檔案", "path", 44),
    ("行", "line", 7), ("子系統", "area", 24), ("頂層目錄", "top", 11),
    ("類別", "class", 8), ("標記", "markers", 11), ("函式", "func", 22),
    ("最後修改", "blame_date", 11), ("年數", "age", 7),
    ("作者", "blame_author", 22), ("初篩", "screen_label", 12),
    ("優先", "screen_prio", 6), ("初篩理由", "screen_why", 60),
    ("判定", "verdict", 11), ("信心", "confidence", 8),
    ("第二審", "verify", 10), ("註解（節錄）", "comment", 70),
]


def styled(ws, row, values, bold=False, fill=None, wrap=False):
    for col, v in enumerate(values, 1):
        c = ws.cell(row=row, column=col, value=v)
        c.font = Font(name=FONT, size=10, bold=bold)
        if fill:
            c.fill = fill
        c.alignment = Alignment(vertical="top", wrap_text=wrap)
    return row + 1


def header(ws, names, widths):
    styled(ws, 1, names, bold=True, fill=HEAD_FILL, wrap=True)
    for i, w in enumerate(widths, 1):
        ws.column_dimensions[get_column_letter(i)].width = w
    ws.freeze_panes = "A2"


def col_of(key):
    for i, (_, k, _) in enumerate(ALL_COLS, 1):
        if k == key:
            return get_column_letter(i)
    raise KeyError(key)


def verify_text(r):
    if "verify_agree" not in r:
        return ""
    if r.get("accepted_by"):
        return "修正後採用"
    return "同意" if r["verify_agree"] else "不同意:%s" % r.get("verify_verdict", "")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("-l", dest="ledger", required=True)
    ap.add_argument("-c", dest="commits")
    ap.add_argument("-o", dest="out", required=True)
    ap.add_argument("--date", required=True)
    args = ap.parse_args()

    recs = [json.loads(l) for l in open(args.ledger) if l.strip()]
    live = [r for r in recs if r["status"] != "gone"]
    live.sort(key=lambda r: (r["path"], r["line"]))
    commits = []
    if args.commits:
        commits = [json.loads(l) for l in open(args.commits) if l.strip()]
    committed = {i: c for c in commits for i in c.get("ids", [])}
    cats = {r["id"]: {k: r["fix_" + k] for k in ("category", "severity", "cluster")
                      if "fix_" + k in r}
            for r in live if "fix_severity" in r}
    head = live[0].get("head", "") if live else ""
    n = len(live)

    wb = Workbook()
    readme = wb.active
    readme.title = "README"
    summary = wb.create_sheet("Summary")
    triage = wb.create_sheet("Triage")
    byarea = wb.create_sheet("By area")
    csheet = wb.create_sheet("Commits")
    psheet = wb.create_sheet("Patches")
    allws = wb.create_sheet("All items")
    ref = "'All items'!$%s$2:$%s$%d"

    # All items
    header(allws, [h for h, _, _ in ALL_COLS], [w for _, _, w in ALL_COLS])
    for i, r in enumerate(live, 2):
        vals = []
        for _, k, _ in ALL_COLS:
            if k == "top":
                v = r["path"].split("/")[0] if "/" in r["path"] else "(top)"
            elif k == "markers":
                v = ",".join(r.get("markers", []))
            elif k == "verify":
                v = verify_text(r)
            elif k == "comment":
                v = " ".join(r.get("comment", "").split())[:300]
            else:
                v = r.get(k, "")
            vals.append(v)
        styled(allws, i, vals)
        c = allws.cell(row=i, column=3)
        c.hyperlink = UPSTREAM % (r.get("head", head), r["path"], r["line"])
        c.font = Font(name=FONT, size=10, color="1F4E99", underline="single")
    allws.auto_filter.ref = "A1:%s%d" % (get_column_letter(len(ALL_COLS)), n + 1)

    # Triage
    tri = [r for r in live if r.get("verdict")]
    order = {v: i for i, v in enumerate(VERDICTS)}
    sev = {v: i for i, v in enumerate(SEVERITY)}
    tri.sort(key=lambda r: (order.get(r["verdict"], 9),
                            sev.get(cats.get(r["id"], {}).get("severity"), 9),
                            r["path"], r["line"]))
    tcols = [("ID", 15), ("檔案:行", 46), ("子系統", 22), ("標記", 9),
             ("判定", 10), ("信心", 8), ("第二審", 12), ("嚴重度", 8),
             ("類型", 14), ("摘要", 50), ("理由（英文）", 80), ("修正方案", 70),
             ("工作量", 7), ("風險", 8), ("Patch", 7), ("證據", 50),
             ("處理狀態", 12), ("Commit", 14), ("群組", 18), ("初篩", 11)]
    header(triage, [h for h, _ in tcols], [w for _, w in tcols])
    track_col = get_column_letter([h for h, _ in tcols].index("處理狀態") + 1)
    sev_col = get_column_letter([h for h, _ in tcols].index("嚴重度") + 1)
    dv = DataValidation(type="list", formula1='"%s"' % ",".join(TRACK),
                        allow_blank=True)
    triage.add_data_validation(dv)
    for i, r in enumerate(tri, 2):
        c = committed.get(r["id"])
        k = cats.get(r["id"], {})
        vals = [r["id"], "%s:%d" % (r["path"], r["line"]), r.get("area", ""),
                ",".join(r.get("markers", [])), r["verdict"],
                r.get("confidence", ""), verify_text(r), k.get("severity", ""),
                k.get("category", ""), r.get("summary_zh", ""),
                r.get("rationale", ""), r.get("fix", ""), r.get("effort", ""),
                r.get("risk", ""), "有" if r.get("patch") else "",
                "\n".join(r.get("evidence", []) or []),
                r.get("track") or ("已提交到分支" if c else "待處理"),
                c["sha"][:12] if c else "", k.get("cluster", ""),
                r.get("screen_label", "")]
        styled(triage, i, vals, wrap=True)
        cell = triage.cell(row=i, column=2)
        cell.hyperlink = UPSTREAM % (r.get("head", head), r["path"], r["line"])
        cell.font = Font(name=FONT, size=10, color="1F4E99", underline="single")
        dv.add("%s%d" % (track_col, i))
    triage.auto_filter.ref = "A1:%s%d" % (get_column_letter(len(tcols)),
                                          max(2, len(tri) + 1))

    # Summary: formulas over All items
    summary.column_dimensions["A"].width = 30
    summary.column_dimensions["B"].width = 12
    summary.column_dimensions["C"].width = 60
    row = styled(summary, 1, ["FreeBSD src 標記審查摘要", None, None], bold=True)
    row = styled(summary, row, ["執行日期", args.date])
    row = styled(summary, row, ["main HEAD", head[:12]])
    row = styled(summary, row, ["仍在樹中的標記註解", "=COUNTA(%s)" % (ref % ("A", "A", n + 1)),
                                "All items 的列數"])
    row += 1
    row = styled(summary, row, ["初篩標籤", "數量", "說明"], bold=True, fill=HEAD_FILL)
    notes = {"STALE": "很可能已過時", "ACTIONABLE": "仍有效且看得出修法",
             "NOTE": "說明性質，暫不處理", "NOT_MARKER": "不是待辦標記",
             "LOOK": "需要細查"}
    for lab in LABELS:
        row = styled(summary, row, [lab, '=COUNTIFS(%s,"%s")' % (
            ref % (col_of("screen_label"), col_of("screen_label"), n + 1), lab), notes[lab]])
    row = styled(summary, row, ["（尚未初篩）", '=COUNTIFS(%s,"")' % (
        ref % (col_of("screen_label"), col_of("screen_label"), n + 1)), ""])
    row += 1
    row = styled(summary, row, ["深入審查判定", "數量", "其中第二審同意"], bold=True,
                 fill=HEAD_FILL)
    vcol = ref % (col_of("verdict"), col_of("verdict"), n + 1)
    acol = ref % (col_of("verify"), col_of("verify"), n + 1)
    for v in VERDICTS:
        row = styled(summary, row, [v, '=COUNTIFS(%s,"%s")' % (vcol, v),
                                    '=COUNTIFS(%s,"%s",%s,"同意")' % (vcol, v, acol)])
    row += 1
    if cats:
        row = styled(summary, row, ["FIX/DESIGN 嚴重度", "數量", "依 Triage 表計算"],
                     bold=True, fill=HEAD_FILL)
        srng = "Triage!$%s$2:$%s$%d" % (sev_col, sev_col, max(2, len(tri) + 1))
        for v in SEVERITY:
            row = styled(summary, row, [v, '=COUNTIFS(%s,"%s")' % (srng, v), ""])
        row += 1
    row = styled(summary, row, ["頂層目錄", "數量", ""], bold=True, fill=HEAD_FILL)
    tops = Counter(r["path"].split("/")[0] if "/" in r["path"] else "(top)" for r in live)
    for t, _ in tops.most_common():
        row = styled(summary, row, [t, '=COUNTIFS(%s,"%s")' % (
            ref % (col_of("top"), col_of("top"), n + 1), t), ""])

    # By area
    acols = ["子系統", "總數"] + LABELS + ["已深入審查", "REMOVE/REWORD"]
    header(byarea, acols, [26, 8] + [11] * len(LABELS) + [11, 14])
    areas = Counter(r.get("area", "") for r in live)
    arng = ref % (col_of("area"), col_of("area"), n + 1)
    lrng = ref % (col_of("screen_label"), col_of("screen_label"), n + 1)
    for i, (a, _) in enumerate(areas.most_common(), 2):
        vals = [a, "=COUNTIFS(%s,$A%d)" % (arng, i)]
        vals += ['=COUNTIFS(%s,$A%d,%s,"%s")' % (arng, i, lrng, lab) for lab in LABELS]
        vals.append('=COUNTIFS(%s,$A%d,%s,"<>")' % (arng, i, vcol))
        vals.append('=COUNTIFS(%s,$A%d,%s,"REMOVE")+COUNTIFS(%s,$A%d,%s,"REWORD")' % (
            arng, i, vcol, arng, i, vcol))
        styled(byarea, i, vals)
    byarea.auto_filter.ref = "A1:%s%d" % (get_column_letter(len(acols)), len(areas) + 1)

    # Commits
    header(csheet, ["Commit", "標題", "項目數", "檔案數"], [14, 80, 8, 8])
    for i, c in enumerate(commits, 2):
        styled(csheet, i, [c["sha"][:12], c["subject"], len(c.get("ids", [])),
                           c.get("files", "")])

    # Patches: one row per FIX item with a patch; a cell holds 32,767 characters
    header(psheet, ["ID", "檔案:行", "第二審", "嚴重度", "Patch"], [15, 46, 12, 8, 120])
    prow = 2
    for r in tri:
        if r.get("verdict") == "FIX" and r.get("patch"):
            styled(psheet, prow, [r["id"], "%s:%d" % (r["path"], r["line"]), verify_text(r),
                                  cats.get(r["id"], {}).get("severity", ""),
                                  r["patch"][:32000]])
            prow += 1

    # README
    readme.column_dimensions["A"].width = 18
    readme.column_dimensions["B"].width = 100
    lines = [
        ("FreeBSD src TODO/FIXME/XXX 註解審查追蹤表", None),
        ("產生日期", args.date),
        ("基準", "freebsd/main %s" % head[:12]),
        ("Summary", "各類數量；全部是 COUNTIFS 公式，依 All items 計算。"),
        ("Triage", "已深入審查的項目。「處理狀態」欄可下拉選擇，手動更新。"),
        ("By area", "依子系統統計初篩標籤與審查進度（公式）。"),
        ("Commits", "已提交到審查分支的 commit。"),
        ("Patches", "FIX 項目附的修正 patch（unified diff，尚未編譯測試）；複製儲存格內容即可用 git apply 套用。"),
        ("All items", "樹中所有含標記的註解區塊，一列一筆；檔案欄連到 GitHub 上該行。"),
        ("初篩標籤", "STALE 很可能已過時；ACTIONABLE 仍有效且可修；NOTE 說明性質；"
                     "NOT_MARKER 不是待辦標記；LOOK 需要細查。"),
        ("判定", "REMOVE 刪除；REWORD 改寫；FIX 可修正；DESIGN 需要設計討論；"
                 "KEEP 保留；NOT_MARKER 非標記；UNSURE 證據不足。"),
        ("嚴重度", "FIX/DESIGN 項目：high 使用者可能遇到當機、記憶體毀損、資料遺失或安全問題；"
                   "medium 可觀察到的錯誤行為或需特殊條件的潛在問題；low 目前沒有使用者可見的影響。"
                   "「Patch」欄標示是否附有修正 patch（尚未編譯測試）。"),
        ("狀態", "new 未初篩；screened 已初篩；triaged 已審查；verified 第二審同意；"
                 "disputed 第二審不同意；committed 已提交。「第二審」欄的「修正後採用」"
                 "表示第二審同意判定但修正了文字，經人工核對後採用修正版。"),
        ("注意", "所有判定與修改都由 AI 產生，送上游前需要人工審查（見 CONTRIBUTING.md）。"),
    ]
    for i, (a, b) in enumerate(lines, 1):
        styled(readme, i, [a, b], wrap=True)
        readme.cell(row=i, column=1).font = Font(name=FONT, size=10, bold=True)

    wb.save(args.out)


if __name__ == "__main__":
    main()
