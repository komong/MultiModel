"""精确修复 litellm_proxy_extras/utils.py 中 prisma subprocess 调用加 shell=True。

策略：逐行扫描，用括号计数器定位完整的 subprocess.run( ... ) 块，
只在包含 _get_prisma_command() 的块中添加 shell=True。
"""
import re

target = r"C:\litellm-env\Lib\site-packages\litellm_proxy_extras\utils.py"

with open(target, "r", encoding="utf-8") as f:
    content = f.read()

# 使用正则表达式匹配 subprocess.run( ... ) 块
# 包括多行的情况
# 关键：匹配到闭合 ) 为止

def find_subprocess_blocks(text):
    """找到所有 subprocess.run( ... ) 块的起止位置。"""
    blocks = []
    i = 0
    while i < len(text):
        # 找到 subprocess.run(
        idx = text.find('subprocess.run(', i)
        if idx == -1:
            break
        
        # 从 ( 开始计数括号深度
        start = idx
        paren_pos = idx + len('subprocess.run')
        depth = 0
        j = paren_pos
        while j < len(text):
            if text[j] == '(':
                depth += 1
            elif text[j] == ')':
                depth -= 1
                if depth == 0:
                    blocks.append((start, j + 1))
                    break
            j += 1
        
        i = j + 1 if j < len(text) else len(text)
    
    return blocks

blocks = find_subprocess_blocks(content)
print(f"找到 {len(blocks)} 个 subprocess.run 块")

count = 0
# 从后往前替换以保持偏移量正确
for start, end in reversed(blocks):
    block = content[start:end]
    if '_get_prisma_command()' in block and 'shell=True' not in block:
        # 找到最后的 ) 并替换为 , shell=True)
        new_block = block[:-1].rstrip() + ', shell=True)'
        content = content[:start] + new_block + content[end:]
        count += 1
        # 显示行号
        line_num = content[:start].count('\n') + 1
        print(f"  修复第 ~{line_num} 行的 subprocess.run")

print(f"共修改 {count} 处")

with open(target, "w", encoding="utf-8", newline="") as f:
    f.write(content)

print("写入完成")
