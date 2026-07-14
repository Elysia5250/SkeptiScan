"""
经验数据库
存储用户纠正记录，供 pattern_learner 检索
"""

import os
import sqlite3
import json
from datetime import datetime
from pathlib import Path

DB_DIR = Path(__file__).parent.parent / "data"
DB_PATH = DB_DIR / "experience.db"


def _get_conn() -> sqlite3.Connection:
    DB_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = _get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS corrections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            original_text TEXT NOT NULL,
            original_verdict TEXT NOT NULL,
            corrected_verdict TEXT NOT NULL,
            risk_level INTEGER DEFAULT 0,
            notes TEXT DEFAULT '',
            keywords TEXT DEFAULT '[]',
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_corrections_keywords
        ON corrections(keywords)
    """)
    conn.commit()
    conn.close()


def store(original_text: str, original_verdict: str,
          corrected_verdict: str, risk_level: int = 0,
          notes: str = "") -> int:
    """存储一条纠正记录"""
    from services.risk_rules import detect_risk_keywords
    kw = detect_risk_keywords(original_text)
    all_kw = kw["all_matched"]
    # 也提取 KB 关键词
    from services.scam_knowledge_base import scan_text
    kb = scan_text(original_text)
    kb_terms = [t for t, _, _ in kb.get("pseudo_terms", [])]
    combined = list(set(all_kw + kb_terms))

    conn = _get_conn()
    conn.execute("""
        INSERT INTO corrections
            (original_text, original_verdict, corrected_verdict,
             risk_level, notes, keywords)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (original_text[:1000], original_verdict, corrected_verdict,
          risk_level, notes[:500], json.dumps(combined, ensure_ascii=False)))
    conn.commit()
    row_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.close()
    print(f"[Experience] 纠正已记录 (id={row_id}, {original_verdict}→{corrected_verdict})")
    return row_id


def query_similar(text: str, max_results: int = 5) -> list[dict]:
    """
    检索与当前文本相似的历史纠正记录
    通过共同关键词数量 + 文本内容重叠度评分
    """
    from services.risk_rules import detect_risk_keywords
    from services.scam_knowledge_base import scan_text

    # 提取当前文本的关键词
    kw = detect_risk_keywords(text)
    current_kw = set(kw["all_matched"])
    kb = scan_text(text)
    kb_terms = set(t for t, _, _ in kb.get("pseudo_terms", []))
    current_kw |= kb_terms

    conn = _get_conn()
    rows = conn.execute("""
        SELECT * FROM corrections
        ORDER BY created_at DESC
        LIMIT 200
    """).fetchall()
    conn.close()

    if not current_kw:
        return []

    scored = []
    for row in rows:
        stored_kw = set(json.loads(row["keywords"]))
        overlap = len(current_kw & stored_kw)
        if overlap == 0:
            continue
        # 分数 = 共同关键词数 / 当前总关键词数 × 100
        score = round(overlap / max(len(current_kw), 1) * 100, 1)
        scored.append((score, {
            "id": row["id"],
            "original_text": row["original_text"][:200],
            "original_verdict": row["original_verdict"],
            "corrected_verdict": row["corrected_verdict"],
            "risk_level": row["risk_level"],
            "notes": row["notes"],
            "created_at": row["created_at"],
            "keywords": stored_kw,
            "match_score": score,
        }))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [item for _, item in scored[:max_results]]


def build_learning_context(text: str) -> str:
    """为当前输入构建自学习注入文本"""
    similar = query_similar(text)
    if not similar:
        return ""

    parts = []
    # 按纠正类型聚合
    by_correction = {}
    for item in similar:
        key = f"{item['original_verdict']}→{item['corrected_verdict']}"
        by_correction.setdefault(key, []).append(item)

    total = len(similar)
    parts.append(f"【基于 {total} 条历史纠正经验的参考】")
    parts.append("以下类似案例曾被用户纠正过，请参考：")

    for correction_type, items in by_correction.items():
        parts.append(f"\n- 纠正模式 {correction_type}（共 {len(items)} 条）：")
        for item in items[:2]:
            kw_str = "、".join(list(item["keywords"])[:5]) if item["keywords"] else ""
            note = f" — {item['notes'][:60]}" if item["notes"] else ""
            parts.append(f"  · \"{item['original_text'][:80]}...\"{note}")
            parts.append(f"    （关键词：{kw_str}，匹配度 {item['match_score']}%）")

    parts.append("\n请在评分时参考这些历史纠正经验。")
    return "\n".join(parts)
