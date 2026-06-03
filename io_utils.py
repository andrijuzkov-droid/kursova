```python
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
```

## Файл: `data/sample_edges.csv`

```csv
source,target
Gateway,DMZ
Gateway,Admin-PC
DMZ,Web-Server
DMZ,Mail-Server
Web-Server,DB-Server
Mail-Server,DB-Server
DB-Server,Backup
Admin-PC,HR-PC
Admin-PC,Dev-PC
Dev-PC,CI-Server
CI-Server,Repo
Repo,DB-Server
HR-PC,File-Server
File-Server,Backup
```
