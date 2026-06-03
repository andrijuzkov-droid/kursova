from __future__ import annotations

from io import StringIO

import pandas as pd

def parse_uploaded_csv(content: bytes) -> pd.DataFrame:
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        text = content.decode("cp1251")

    df = pd.read_csv(StringIO(text))
    if df.empty:
        raise ValueError("CSV is empty.")
    return df
