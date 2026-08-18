with open('../want/sd=0.5 with less dia 12-2.for', 'r') as f:
    code = f.read()

code = code.replace('DO i=n,1,-1 !RIGHT TO LEFT', 'DO i=n,2,-1 !RIGHT TO LEFT')

with open('../want/sd=0.5 with less dia 12-2.for', 'w') as f:
    f.write(code)
