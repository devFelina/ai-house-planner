import os
import re

def fix_file(filepath):
    with open(filepath, 'r') as f:
        content = f.read()

    # If already fixed or no need to fix
    if '|' not in content:
        return

    # Add Optional to typing import if not present
    if 'from typing import ' in content and 'Optional' not in content:
        content = re.sub(r'(from typing import .*?)(?=\n)', r'\1, Optional, Union', content)
    elif 'import typing' not in content:
        content = 'from typing import Optional, Union\n' + content

    # Replace `X | None` with `Optional[X]`
    content = re.sub(r'([A-Za-z0-9_\[\]]+)\s*\|\s*None', r'Optional[\1]', content)
    
    # Replace `dict | PlotConstraints` -> `Union[dict, PlotConstraints]`
    content = re.sub(r'([A-Za-z0-9_\[\]]+)\s*\|\s*([A-Za-z0-9_\[\]]+)', r'Union[\1, \2]', content)
    # Fix dict | None if previous pass missed due to order
    content = re.sub(r'([A-Za-z0-9_\[\]]+)\s*\|\s*None', r'Optional[\1]', content)

    # Specific fixes for multiple |
    content = content.replace('dict | PlotConstraints | None', 'Optional[Union[dict, PlotConstraints]]')
    content = content.replace('Optional[Union[dict, PlotConstraints]] = None', 'Optional[Union[dict, "PlotConstraints"]] = None')

    with open(filepath, 'w') as f:
        f.write(content)
    print(f"Fixed {filepath}")

for root, _, files in os.walk('app'):
    for f in files:
        if f.endswith('.py'):
            fix_file(os.path.join(root, f))
