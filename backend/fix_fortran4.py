with open('../want/sd=0.5 with less dia 12-2.for', 'r') as f:
    code = f.read()

code = code.replace('call collt(u,v,nodet,nodeteq,temp,ot,w,cx,cy,lx,ly)', 'u=0.d0\n        v=0.d0\n        call collt(u,v,nodet,nodeteq,temp,ot,w,cx,cy,lx,ly)')

with open('../want/sd=0.5 with less dia 12-2.for', 'w') as f:
    f.write(code)
