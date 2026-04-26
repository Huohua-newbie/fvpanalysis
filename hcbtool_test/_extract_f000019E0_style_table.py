# -*- coding: utf-8 -*-
from pathlib import Path
import re
p=Path('fvp_analysis/result/hcbtool_test/Sakura_hcb_ir/Sakura.lua')
lines=p.read_text(encoding='utf-8',errors='replace').splitlines()
# Extract function lines
start=next(i for i,l in enumerate(lines) if l.startswith('function f_000019E0'))
end=next(i for i in range(start+1,len(lines)) if lines[i]=='end')
seg=lines[start:end+1]
# Split by block labels
blocks=[]
cur=[]
for l in seg:
    if '::BB_' in l and cur:
        blocks.append(cur); cur=[l]
    else:
        cur.append(l)
if cur: blocks.append(cur)

# Scan condition blocks followed by action blocks in Lua output structure.
# We manually collect action blocks that contain TextColor/TextOutSize and optional f_0008CC08.
for bi,b in enumerate(blocks):
    text='\n'.join(b)
    if 'TextColor' not in text and 'TextOutSize' not in text:
        continue
    # Infer condition from nearest previous condition block if current block doesn't contain compare itself.
    # Print block id and relevant lines.
    print('\n---BLOCK', bi, b[0].strip())
    # Backtrack previous block for condition lines
    if bi>0:
        prev='\n'.join(blocks[bi-1])
        cm=re.findall(r'S1 = (-?\d+)\n\s*S0 = \(S0 (==|>=|<=) S1\)', prev)
        if cm: print('COND_PREV', cm[-1])
    # current condition maybe
    cm=re.findall(r'S1 = (-?\d+)\n\s*S0 = \(S0 (==|>=|<=) S1\)', text)
    if cm: print('COND_CUR', cm[-1])
    for l in b:
        if 'f_0008CC08' in l or 'TextColor' in l or 'TextOutSize' in l:
            # also print preceding 4 lines for args
            idx=b.index(l)
            for ll in b[max(0,idx-4):idx+1]:
                print(ll)
            print('---')
