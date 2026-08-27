#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
path = ROOT / "scripts" / "update_market_data.py"
text = path.read_text(encoding="utf-8")

text = text.replace(
'''            if "ucits" not in lower_name:\n                continue\n''',
''''''
)

text = text.replace(
'''            try:\n                chart(symbol, "1mo", "1d")\n            except Exception:\n                continue\n\n            clean_id = re.sub(r"[^a-z0-9]+", "-", symbol.lower()).strip("-")''',
'''            try:\n                candidate_chart = chart(symbol, "1y", "1d")\n                if len(series_from_chart(candidate_chart, prefer_adjusted=True)) < 60:\n                    continue\n            except Exception:\n                continue\n\n            clean_id = re.sub(r"[^a-z0-9]+", "-", symbol.lower()).strip("-")'''
)

path.write_text(text, encoding="utf-8")
print("Discovery v2 patch applied")
