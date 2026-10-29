"""RuFlirt local Ollama adapter. Standard library only; bind to loopback.
Requires an authenticated HTTPS reverse proxy for external use.
"""
import json, os, urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

OLLAMA=os.getenv("OLLAMA_URL","http://127.0.0.1:11434").rstrip("/")
MODEL=os.getenv("OLLAMA_MODEL","qwen3:1.7b")
ORIGIN=os.getenv("RUFLIRT_ORIGIN","https://ruslangreen.github.io")
TOKEN=os.getenv("RUFLIRT_ACCESS_TOKEN","")
PROMPT=("Ты быстрый суфлёр для взрослого мужчины в добровольном знакомстве. "
"Напиши ровно одну короткую естественную реплику на русском (5–14 слов). "
"Лёгкий флирт, если уместно, без давления, без выдуманных фактов и без пояснений. "
"Если собеседница не заинтересована — уважай это. Избегай повторов.")
class Handler(BaseHTTPRequestHandler):
 def respond(self,code,obj):
  b=json.dumps(obj,ensure_ascii=False).encode()
  self.send_response(code)
  self.send_header("Content-Type","application/json; charset=utf-8")
  self.send_header("Access-Control-Allow-Origin",ORIGIN)
  self.send_header("Vary","Origin")
  self.send_header("Cache-Control","no-store")
  self.send_header("Content-Length",str(len(b)))
  self.end_headers()
  self.wfile.write(b)
 def do_OPTIONS(self):
  self.send_response(204)
  self.send_header("Access-Control-Allow-Origin",ORIGIN)
  self.send_header("Access-Control-Allow-Methods","POST, OPTIONS")
  self.send_header("Access-Control-Allow-Headers","Content-Type, Authorization")
  self.end_headers()
 def do_POST(self):
  if self.path!="/suggest":return self.respond(404,{"error":"not_found"})
  if self.headers.get("Origin")!=ORIGIN:return self.respond(403,{"error":"origin_denied"})
  if not TOKEN or self.headers.get("Authorization")!="Bearer "+TOKEN:return self.respond(401,{"error":"unauthorized"})
  try:
   n=int(self.headers.get("Content-Length","0"))
   if not 0<n<12000:return self.respond(413,{"error":"invalid_size"})
   body=json.loads(self.rfile.read(n))
   message=str(body.get("text","")).strip()[:500]
   if not message:return self.respond(400,{"error":"empty_text"})
   history=body.get("history",[])
   if not isinstance(history,list):history=[]
   context="\n".join(str(x.get("speaker",""))+": "+str(x.get("text",""))[:250] for x in history[-8:] if isinstance(x,dict))
   payload=json.dumps({"model":MODEL,"stream":False,"prompt":PROMPT+"\nКонтекст:\n"+context+"\nДевушка: "+message+"\nОтвет:","options":{"num_predict":65,"temperature":0.65}}).encode()
   req=urllib.request.Request(OLLAMA+"/api/generate",payload,{"Content-Type":"application/json"})
   with urllib.request.urlopen(req,timeout=8) as r: data=json.load(r)
   reply=str(data.get("response","")).strip().strip('"')[:240]
   self.respond(200,{"suggestion":reply})
  except Exception:
   self.respond(502,{"error":"ollama_unavailable"})
 def log_message(self,*args):pass
if __name__=="__main__":
 ThreadingHTTPServer(("127.0.0.1",int(os.getenv("PORT","8765"))),Handler).serve_forever()
