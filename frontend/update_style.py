import re
import os

css_file = r'C:\Users\Damian Motomboni\Desktop\EMR-SAAS\frontend\src\styles\ConsultationWorkspace.module.css'
with open(css_file, 'r', encoding='utf-8') as f:
    content = f.read()

replacements = [
    (r'background-color:\s*#f5f5f5;', 'background-color: var(--bg-secondary, #f9fafb);'),
    (r'background:\s*#f5f5f5;', 'background: var(--bg-secondary, #f9fafb);'),
    (r'background:\s*#f9f9f9;', 'background: var(--bg-secondary, #f9fafb);'),
    (r'background-color:\s*#f9f9f9;', 'background-color: var(--bg-secondary, #f9fafb);'),
    (r'border:\s*1px\s*solid\s*#e0e0e0;', 'border: 1px solid rgba(128, 128, 128, 0.15);'),
    (r'border-top:\s*2px\s*solid\s*#e0e0e0;', 'border-top: 1px solid rgba(128, 128, 128, 0.1);'),
    (r'border-bottom:\s*2px\s*solid\s*#e0e0e0;', 'border-bottom: 1px solid rgba(128, 128, 128, 0.1);'),
    (r'border-top:\s*1px\s*solid\s*#e0e0e0;', 'border-top: 1px solid rgba(128, 128, 128, 0.15);'),
    (r'border-bottom:\s*1px\s*solid\s*#e0e0e0;', 'border-bottom: 1px solid rgba(128, 128, 128, 0.15);'),
    (r'border:\s*1px\s*solid\s*#ddd;', 'border: 1px solid rgba(128, 128, 128, 0.2);'),
    (r'border-radius:\s*4px;', 'border-radius: 8px;'),
    (r'border-radius:\s*6px;', 'border-radius: 12px;'),
    (r'border-radius:\s*8px;', 'border-radius: 16px;'),
    (r'box-shadow:\s*0\s*1px\s*3px\s*rgba\(0,\s*0,\s*0,\s*0\.1\);', 'box-shadow: 0 4px 20px rgba(0, 0, 0, 0.03);'),
    (r'box-shadow:\s*0\s*2px\s*4px\s*rgba\(0,\s*0,\s*0,\s*0\.1\);', 'box-shadow: 0 4px 20px rgba(0, 0, 0, 0.05);'),
    (r'box-shadow:\s*0\s*2px\s*8px\s*rgba\(0,\s*0,\s*0,\s*0\.1\);', 'box-shadow: 0 8px 30px rgba(0, 0, 0, 0.08);'),
    (r'box-shadow:\s*0\s*-2px\s*4px\s*rgba\(0,\s*0,\s*0,\s*0\.1\);', 'box-shadow: 0 -4px 20px rgba(0, 0, 0, 0.05);'),
    (r'background-color:\s*#2196f3;', 'background: linear-gradient(135deg, #3b82f6, #2563eb);'),
    (r'background-color:\s*#4caf50;', 'background: linear-gradient(135deg, #10b981, #059669);'),
    (r'background-color:\s*#f44336;', 'background: linear-gradient(135deg, #ef4444, #dc2626);'),
    (r'background-color:\s*#9c27b0;', 'background: linear-gradient(135deg, #8b5cf6, #6d28d9);'),
    (r'background-color:\s*#1976d2;', 'background: linear-gradient(135deg, #2563eb, #1d4ed8);'),
    (r'background-color:\s*#45a049;', 'background: linear-gradient(135deg, #059669, #047857);'),
    (r'background-color:\s*#d32f2f;', 'background: linear-gradient(135deg, #dc2626, #b91c1c);'),
    (r'background-color:\s*#7b1fa2;', 'background: linear-gradient(135deg, #7c3aed, #5b21b6);'),
    (r'padding:\s*0\.5rem\s*1rem;', 'padding: 0.75rem 1.5rem;'),
    (r'padding:\s*0\.75rem\s*1\.5rem;', 'padding: 1rem 2rem;'),
    (r'color:\s*#333;', 'color: var(--text-primary);'),
    (r'color:\s*#666;', 'color: var(--text-secondary);'),
    (r'font-weight:\s*600;', 'font-weight: 700;'),
    (r'background:\s*white;', 'background: var(--bg-primary, white);'),
    (r'background-color:\s*white;', 'background-color: var(--bg-primary, white);'),
    (r'padding:\s*1.5rem\s*2rem;', 'padding: 2.5rem 3rem;'),
    (r'padding:\s*1.5rem;', 'padding: 2rem;'),
    (r'font-size:\s*1rem;', 'font-size: 1.05rem;'),
]

for old, new in replacements:
    content = re.sub(old, new, content)

with open(css_file, 'w', encoding='utf-8') as f:
    f.write(content)

print(f"Updated {css_file} successfully")
