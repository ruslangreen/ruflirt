"""RuFlirt AI backend. Python 3.11+, no third-party packages required.
Run behind HTTPS reverse proxy. Set OPENAI_API_KEY and RUFLIRT_ORIGIN.
"""
import json, os, urllib.request, urllib.error
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

ORIGIN=os.getenv("RUFLIRT_ORIGIN","https://ruslangreen.github.io")
KEY=os.getenv("OPENAI_API_KEY","")
MODEL=os.getenv("RUFLIRT_MODEL","gpt-4.1-mini")
SYSTEM=("Ты суфлёр для Руслана, 42 года, в добровольном разговоре со взрослой девушкой. "
"Предложи ОДНУ короткую естественную реплику на русском, 5–15 слов. "
"Лёгкий юмор и флирт только если собеседница проявляет интерес. "
"Не придумывай факты, не дави, не используй манипуляции и шаблонные подкаты. "
"Учитывай историю, избегай повторов. Верни только фразу без пояснений.")
class Handler(BaseHTTPRequestHandler):
 def send(self,code,obj):
  data=json.dumps(obj,ensure_ascii=False).encode()
  self.send_response(code)
  self.send_header("Content-Type","application/json; charset=utf-8")
  self.send_header("Content-Length",str(len(data)))
  self.send_header("Access-Control-Allow-Origin",ORIGIN)
  self.send_header("Vary","Origin")
  self.send_header("Cache-Control","no-store")
  self.end_headers();self.wfile.write(data)
 def do_OPTIONS(self):
  self.send_response(204)
  self.send_header("Access-Control-Allow-Origin",ORIGIN)
  self.send_header("Access-Control-Allow-Methods","POST, OPTIONS")
  self.send_header("Access-Control-Allow-Headers","Content-Type")
  self.end_headers()
 def do_POST(self):
  if urlparse(self.path).path!="/suggest":return self.send(404,{"error":"not_found"})
  if self.headers.get("Origin")!=ORIGIN:return self.send(403,{"error":"origin_denied"})
  try:
   size=int(self.headers.get("Content-Length","0"))
   if not 0<size<=12000:return self.send(413,{"error":"invalid_size"})
   body=json.loads(self.rfile.read(size))
   latest=str(body.get("text",""))[:600].strip()
   if not latest:return self.send(400,{"error":"empty_text"})
   history=body.get("history",[])
   if not isinstance(history,list):history=[]
   context="\n".join(str(item.get("speaker",""))+": "+str(item.get("text",""))[:400] for item in history[-8:] if isinstance(item,dict))
   if not KEY:return self.send(503,{"error":"api_key_not_configured"})
   payload=json.dumps({"model":MODEL,"messages":[{"role":"system","content":SYSTEM},{"role":"user","content":"Контекст:\n"+context+"\nПоследняя реплика девушки: "+latest}],"max_tokens":90,"temperature":0.8}).encode()
   req=urllib.request.Request("https://api.openai.com/v1/chat/completions",payload,{"Authorization":"Bearer "+KEY,"Content-Type":"application/json"})
   with urllib.request.urlopen(req,timeout=4) as response: result=json.load(response)
   answer=result["choices"][0]["message"]["content"].strip().strip('"')
   return self.send(200,{"suggestion":answer[:240]})
  except Exception:
   return self.send(502,{"error":"ai_unavailable"})
 def log_message(self,*args):pass
if __name__=="__main__":
 ThreadingHTTPServer(("127.0.0.1",int(os.getenv("PORT","8765"))),Handler).serve_forever()
