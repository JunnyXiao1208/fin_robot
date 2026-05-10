"""子进程量化数据获取器"""
import os, sys, json
for k in ["HTTP_PROXY","HTTPS_PROXY","http_proxy","https_proxy"]:
    os.environ.pop(k, None)
import akshare as ak

code = sys.argv[1]
df = ak.fund_etf_hist_em(symbol=code, period="daily", start_date="20241001")
if df is not None and not df.empty:
    print(df.to_json(orient="records"))
else:
    print("", end="")
