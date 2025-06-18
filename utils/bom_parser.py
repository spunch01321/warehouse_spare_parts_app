import pandas as pd

def parse_bom(file):
    df = pd.read_excel(file)
    required = "Part Number"
    if required not in df.columns:
        raise ValueError(f"{required} column missing in BOM")
    return df
