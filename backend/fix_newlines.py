import re
with open('app/services/demo_solver.py', 'r') as f:
    text = f.read()

# Replace trailing newline in string literals
text = text.replace('"OBST"\\n\n\')', '"OBST"\\n\')')
text = text.replace('F=POINT\\n\n\')', 'F=POINT\\n\')')
text = text.replace('int(obstacle[row,col])}\\n\n\')', 'int(obstacle[row,col])}\\n\')')
text = text.replace('"TEMP"\\n\n\')', '"TEMP"\\n\')')
text = text.replace('st.flat[idx]:.4f}\\n\n\')', 'st.flat[idx]:.4f}\\n\')')
text = text.replace('available in ParaView\\n\n\', ha=', 'available in ParaView\\n\', ha=')
text = text.replace('"OBST"\n\')', '"OBST"\\n\')')
text = text.replace('F=POINT\n\')', 'F=POINT\\n\')')
text = text.replace('int(obstacle[row,col])}\n\')', 'int(obstacle[row,col])}\\n\')')
text = text.replace('"TEMP"\n\')', '"TEMP"\\n\')')
text = text.replace('st.flat[idx]:.4f}\n\')', 'st.flat[idx]:.4f}\\n\')')
text = text.replace('available in ParaView\n\', ha=', 'available in ParaView\\n\', ha=')

with open('app/services/demo_solver.py', 'w') as f:
    f.write(text)
