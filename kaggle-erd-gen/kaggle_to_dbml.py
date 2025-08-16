#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
kaggle_to_dbml.py
- CSV 폴더를 읽어 테이블 메타를 추론하고
  1) PK 후보(단일/복합) 자동 선정
  2) 같은 이름의 컬럼을 기준으로 값 분포를 비교하여 FK(일대다/다대일/일대일) 추정
  3) dbdiagram.io에 붙여넣을 수 있는 DBML(schema.dbml)과 리포트(report.md) 생성
"""

import os
import re
import sys
import argparse
import pathlib
import itertools
from typing import Dict, List, Tuple, Optional

import pandas as pd
from html import escape

try:
    from graphviz import Digraph
except Exception:
    Digraph = None

# ------------------------------------------------------------
# 유틸
# ------------------------------------------------------------
def snake(s: str) -> str:
    s = s.strip()
    s = re.sub(r'[\s\-]+', '_', s)
    s = re.sub(r'[^0-9a-zA-Z_]', '', s)
    s = re.sub(r'__+', '_', s)
    return s

def guess_dbml_type(dtype) -> str:
    if pd.api.types.is_datetime64_any_dtype(dtype): return "datetime"
    if pd.api.types.is_integer_dtype(dtype): return "int"
    if pd.api.types.is_float_dtype(dtype): return "float"
    return "string"

# ------------------------------------------------------------
# 메타 구조
# ------------------------------------------------------------
class TableMeta:
    def __init__(self, name: str, df: pd.DataFrame):
        self.name = name
        self.df = df
        self.col_types: Dict[str, str] = {c: guess_dbml_type(df[c].dtype) for c in df.columns}
        self.pk_candidates: List[Tuple[str, ...]] = []
        self.chosen_pk: Optional[Tuple[str, ...]] = None

# ------------------------------------------------------------
# 로딩
# ------------------------------------------------------------
def load_tables(input_dir: pathlib.Path, sample: float) -> Dict[str, TableMeta]:
    tables: Dict[str, TableMeta] = {}
    for csv in sorted(input_dir.glob("*.csv")):
        tname = snake(csv.stem)
        df = pd.read_csv(csv, low_memory=False)
        # 표준화
        df.columns = [snake(c) for c in df.columns]
        # 날짜 추정 파싱(열 이름에 시그널 있으면)
        for c in df.columns:
            if re.search(r'(date|time|timestamp)$', c):
                try:
                    # pandas FutureWarning: errors='ignore' deprecated.
                    # Try coercion; if it fails badly, leave as-is.
                    df[c] = pd.to_datetime(df[c])
                except Exception:
                    try:
                        df[c] = pd.to_datetime(df[c], errors='coerce')
                    except Exception:
                        pass
        # 샘플링
        if 0 < sample < 1.0 and len(df) > 0:
            df = df.sample(frac=sample, random_state=42).reset_index(drop=True)
        tables[tname] = TableMeta(tname, df)
    return tables

# ------------------------------------------------------------
# PK 후보 추정
# ------------------------------------------------------------
def find_pk_candidates(meta: TableMeta, max_comb: int = 2):
    df = meta.df
    n = len(df)
    cols = list(df.columns)
    cands: List[Tuple[str, ...]] = []

    # 단일 후보: NULL 없음 + 유일
    for c in cols:
        s = df[c]
        if s.isna().any(): 
            continue
        if s.nunique(dropna=False) == n:
            cands.append((c,))

    # 복합 후보 (최대 max_comb)
    for k in range(2, min(max_comb, len(cols)) + 1):
        for comb in itertools.combinations(cols, k):
            sub = df[list(comb)]
            if sub.isna().any(axis=None):
                continue
            if sub.drop_duplicates().shape[0] == n:
                cands.append(comb)

    # 정렬: (복합보다 단일 선호) + *_id, id 포함 후보 선호
    def score(pk: Tuple[str, ...]):
        id_bonus = sum(1 for c in pk if c.endswith('_id') or c == 'id')
        return (len(pk), -id_bonus)

    cands_sorted = sorted(cands, key=score)
    meta.pk_candidates = cands_sorted
    meta.chosen_pk = cands_sorted[0] if cands_sorted else None

# ------------------------------------------------------------
# 공통 컬럼 기반 FK 추정 (요청하신 방식)
# ------------------------------------------------------------
def detect_fk_by_common_column(tables: Dict[str, TableMeta], orphan_threshold: float = 0.1):
    """
    두 테이블에 '같은 이름의 컬럼'이 있을 때,
    한쪽은 유일(부모 성격), 다른 쪽은 중복(자식 성격)이면 FK 후보로 간주.
    orphan_threshold: 자식 값 중 부모에 존재하지 않는 값 비율 허용치
    """
    fks: List[Tuple[str, str, str, str, str]] = []  # (child_tbl, child_col, parent_tbl, parent_col, rel)
    for t1, m1 in tables.items():
        df1 = m1.df
        for t2, m2 in tables.items():
            if t1 == t2:
                continue
            df2 = m2.df

            common = sorted(set(df1.columns) & set(df2.columns))
            for col in common:
                s1 = df1[col].dropna()
                s2 = df2[col].dropna()
                if s1.empty or s2.empty:
                    continue

                # 타입 차이 방지: 문자열 비교 세트로 통일
                a = set(s1.astype(str).unique())
                b = set(s2.astype(str).unique())

                uniq1 = (len(a) == len(s1))
                uniq2 = (len(b) == len(s2))
                dup1 = (len(a) < len(s1))
                dup2 = (len(b) < len(s2))

                # 부모/자식 후보 판정
                def orphan_rate(child_set, parent_set):
                    if not child_set:
                        return 0.0
                    return len(child_set - parent_set) / max(1, len(child_set))

                # t1.col이 부모(유일), t2.col이 자식(중복)
                if uniq1 and dup2:
                    orphans = orphan_rate(b, a)
                    if orphans <= orphan_threshold:
                        rel = "1:N"
                        fks.append((t2, col, t1, col, rel))
                # t2.col이 부모(유일), t1.col이 자식(중복)
                elif uniq2 and dup1:
                    orphans = orphan_rate(a, b)
                    if orphans <= orphan_threshold:
                        rel = "1:N"
                        fks.append((t1, col, t2, col, rel))
                # 둘 다 유일 → 1:1 관계 가능
                elif uniq1 and uniq2:
                    # 어느 쪽을 부모로 둘지는 임의. 테이블명이 더 짧은 쪽을 부모로 둠.
                    parent_tbl, child_tbl = (t1, t2) if len(t1) <= len(t2) else (t2, t1)
                    parent_set = a if parent_tbl == t1 else b
                    child_set = b if parent_tbl == t1 else a
                    orphans = orphan_rate(child_set, parent_set)
                    if orphans <= orphan_threshold:
                        rel = "1:1"
                        if parent_tbl == t1:
                            fks.append((t2, col, t1, col, rel))
                        else:
                            fks.append((t1, col, t2, col, rel))
                # 둘 다 중복 → N:N (중간 테이블 없이는 직접 FK 지정이 애매해 스킵)
                else:
                    continue
    # 중복 제거
    uniq = {}
    for ct, cc, pt, pc, rel in fks:
        key = (ct, cc, pt, pc)
        uniq[key] = rel
    return [(ct, cc, pt, pc, uniq[(ct, cc, pt, pc)]) for (ct, cc, pt, pc) in uniq.keys()]

# ------------------------------------------------------------
# DBML 출력
# ------------------------------------------------------------
def to_dbml(tables: Dict[str, TableMeta], fks: List[Tuple[str, str, str, str, str]]) -> str:
    parts: List[str] = []
    for name, meta in tables.items():
        parts.append(f"Table {name} {{")
        for c in meta.df.columns:
            t = meta.col_types[c]
            pkflag = ""
            if meta.chosen_pk and c in meta.chosen_pk and len(meta.chosen_pk) == 1:
                pkflag = " [pk]"
            parts.append(f"  {c} {t}{pkflag}")
        if meta.chosen_pk and len(meta.chosen_pk) > 1:
            cols = ", ".join(meta.chosen_pk)
            parts.append("  indexes {")
            parts.append(f"    ({cols}) [pk]")
            parts.append("  }")
        parts.append("}\n")

    for (ct, cc, pt, pc, rel) in fks:
        parts.append(f"Ref: {ct}.{cc} > {pt}.{pc}  // {rel}")
    return "\n".join(parts)

# ------------------------------------------------------------
# 리포트 출력
# ------------------------------------------------------------
def make_report(tables: Dict[str, TableMeta], fks: List[Tuple[str, str, str, str, str]]) -> str:
    lines: List[str] = []
    lines.append("# PK/FK Inference Report\n")
    for n, m in tables.items():
        lines.append(f"## Table `{n}`")
        lines.append(f"- rows: {len(m.df)}  cols: {len(m.df.columns)}")
        lines.append(f"- chosen PK: {(' + '.join(m.chosen_pk)) if m.chosen_pk else '(none)'}")
        lines.append("")
    if fks:
        lines.append("## FK candidates")
        for (ct, cc, pt, pc, rel) in fks:
            lines.append(f"- {ct}.{cc} -> {pt}.{pc}  ({rel})")
    else:
        lines.append("## FK candidates")
        lines.append("- (none)")
    return "\n".join(lines)

def render_erd_graphviz(tables: Dict[str, TableMeta],
                        fks: List[Tuple[str, str, str, str, str]],
                        erd_path: pathlib.Path) -> None:
    if Digraph is None:
        print("[WARN] graphviz is not installed. Skip ERD image. Run: pip install graphviz && brew install graphviz (macOS)")
        return
    # Ensure file extension and directory
    erd_path = erd_path if erd_path.suffix else erd_path.with_suffix('.png')
    erd_path.parent.mkdir(parents=True, exist_ok=True)
    fmt = erd_path.suffix.lstrip('.') or 'png'

    # Helper: HTML-like label for a table (with column rows + ports)
    def _html_table_label(meta: TableMeta) -> str:
        header = f'<TR><TD BGCOLOR="lightgray" ALIGN="CENTER"><B>{escape(meta.name)}</B></TD></TR>'
        rows = []
        pkset = set(meta.chosen_pk) if meta.chosen_pk else set()
        for c in meta.df.columns:
            t = meta.col_types.get(c, "string")
            pkmark = " <B>(pk)</B>" if c in pkset and len(pkset) == 1 else ""
            # Use PORT to allow edges to connect to specific columns
            rows.append(
                f'<TR><TD ALIGN="LEFT" PORT="{escape(c)}"><FONT FACE="monospace">{escape(c)}</FONT> : {escape(t)}{pkmark}</TD></TR>'
            )
        if meta.chosen_pk and len(pkset) > 1:
            comb = ", ".join(meta.chosen_pk)
            rows.append(
                f'<TR><TD ALIGN="LEFT"><I>PK: ({escape(comb)})</I></TD></TR>'
            )
        body = "\n".join(rows)
        return f'<<TABLE BORDER="1" CELLBORDER="0" CELLPADDING="4" CELLSPACING="0">{header}{body}</TABLE>>'

    dot = Digraph(name='ERD', format=fmt)
    dot.attr('graph', rankdir='LR', splines='ortho')
    dot.attr('node', shape='plaintext')

    # Nodes (tables with columns)
    for name in sorted(tables.keys()):
        meta = tables[name]
        dot.node(name, label=_html_table_label(meta))

    # Edges: parent -> child, connect to column ports
    for (child_tbl, child_col, parent_tbl, parent_col, rel) in fks:
        # Ports (column names) are already snake-cased in our loader
        tail = f"{parent_tbl}:{parent_col}"
        head = f"{child_tbl}:{child_col}"
        dot.edge(tail, head, label=rel, arrowsize="0.7")

    # Render to file
    dot.render(filename=erd_path.stem, directory=str(erd_path.parent), cleanup=True)
    print(f"[OK] ERD image written to {erd_path}")

# ------------------------------------------------------------
# 메인
# ------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, help="CSV 폴더 경로")
    ap.add_argument("--output", default="schema.dbml", help="DBML 출력 파일")
    ap.add_argument("--report", default="report.md", help="리포트 출력 파일")
    ap.add_argument("--max-comb", type=int, default=2, help="복합 PK 최대 컬럼 수")
    ap.add_argument("--orphan-threshold", type=float, default=0.1, help="FK 추정 시 허용 orphan 비율")
    ap.add_argument("--sample", type=float, default=1.0, help="샘플링 비율(0~1)")
    ap.add_argument("--erd", help="ERD 이미지 파일 경로")
    ap.add_argument("--verbose", action="store_true", help="진행 로그를 자세히 출력")
    args = ap.parse_args()

    if args.verbose:
        print(f"[INFO] script: {os.path.realpath(__file__)}")
        print(f"[INFO] input : {args.input}")
        print(f"[INFO] output: {args.output}")
        print(f"[INFO] report: {args.report}")
        print(f"[INFO] erd   : {args.erd if args.erd else '(none)'}")

    inp = pathlib.Path(args.input)
    if not inp.exists():
        print(f"[ERR] not found: {inp}")
        sys.exit(1)

    tables = load_tables(inp, args.sample)
    if not tables:
        print("[ERR] no CSVs found")
        sys.exit(2)

    # PK 후보 및 선택
    for meta in tables.values():
        find_pk_candidates(meta, args.max_comb)

    # FK 추정: 같은 이름의 컬럼 기준 + 값 분포 비교
    fks = detect_fk_by_common_column(tables, args.orphan_threshold)

    # 출력
    dbml = to_dbml(tables, fks)
    with open(args.output, "w", encoding="utf-8") as f:
        f.write(dbml)

    rep = make_report(tables, fks)
    with open(args.report, "w", encoding="utf-8") as f:
        f.write(rep)

    # ERD 이미지 생성 옵션 처리
    if getattr(args, 'erd', None):
        erd_arg = pathlib.Path(args.erd)
        if erd_arg.name == args.erd:  # 디렉토리 없이 파일명만 준 경우
            erd_path = pathlib.Path(args.output).parent / erd_arg
        else:
            erd_path = erd_arg
        if args.verbose:
            print(f"[INFO] ERD will be written to: {erd_path}")
        render_erd_graphviz(tables, fks, erd_path)

    if args.verbose:
        print(f"[OK] wrote DBML: {args.output}")
        print(f"[OK] wrote report: {args.report}")
        if getattr(args, 'erd', None):
            print(f"[OK] ERD target: {erd_path}")
    else:
        print(f"[OK] wrote {args.output}, {args.report}")

if __name__ == "__main__":
    pd.options.mode.copy_on_write = True
    main()