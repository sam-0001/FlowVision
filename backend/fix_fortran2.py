with open('../want/sd=0.5 with less dia 12-2.for', 'r') as f:
    code = f.read()

code = code.replace('integer xll,xuu,yll,yuu,p,q\n      integer lx,ly', 'integer xll,xuu,yll,yuu,p,q')

with open('../want/sd=0.5 with less dia 12-2.for', 'w') as f:
    f.write(code)
