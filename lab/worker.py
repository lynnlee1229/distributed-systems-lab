"""A separate owned worker process, paused by the experiment parent."""
import json,sys
from .runtime import post
print('ready',flush=True)
d=json.loads(sys.stdin.readline())
print(json.dumps({mode:post(d['url']+'/write',{'mode':mode,'token':d['token'],'value':'A-late'}) for mode in ('plain','fenced')}),flush=True)
