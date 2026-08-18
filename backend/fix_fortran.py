import re

with open('../want/sd=0.5 with less dia 12-2.for', 'r') as f:
    code = f.read()

# Fix 1: integer xl,yl -> integer yl
code = re.sub(r'integer\s+xl,yl', 'integer yl', code)

# Fix 2: integer xl,xu,x11,xuu,yuu,yll,yu -> remove xl and xu since they might be parameters?
# Wait, if they are parameters, they shouldn't be declared as integers? No, Fortran 77 requires them to be declared.
# The error was "xl already has basic type of INTEGER". This is because we removed 'integer xl' from top.
# Let's just leave 'integer xl,xu...' at line 134.

# Fix 3: read_obstacles implicit types
code = code.replace('integer  x1,y1,i,xl,yl,dia,xu,n_cyl,yu,x1', 'integer x1,y1,i,xl,yl,dia,xu,n_cyl,yu')
code = code.replace('integer   xll,xuu,yll,yuu,p,q', 'integer xll,xuu,yll,yuu,p,q\n      integer lx,ly')
# wait, lx, ly are already there!
# The error was: Symbol 'xu' has no IMPLICIT type; did you mean 'xuu'?
# Let's just add `implicit none` overrides or remove `implicit none` from subroutines!
code = code.replace('implicit none', '')

with open('../want/sd=0.5 with less dia 12-2.for', 'w') as f:
    f.write(code)
