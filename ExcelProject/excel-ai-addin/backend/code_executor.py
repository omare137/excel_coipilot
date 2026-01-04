"""
code_executor.py
Executes GPT-generated Python code with df in scope.
"""
import sys
import traceback
import re
import matplotlib.pyplot as plt

def clean_code(code):
    """Removes markdown formatting from GPT-generated code."""
    # Remove ```python and ``` markers
    code = re.sub(r'```python\s*', '', code)
    code = re.sub(r'```\s*$', '', code)
    # Remove leading/trailing whitespace
    code = code.strip()
    return code

def execute_code(code, df, extra_globals=None):
    """Executes the provided Python code with df available as a global variable."""
    # Clean the code first
    code = clean_code(code)
    
    local_vars = {}
    global_vars = {
        "df": df,
        "plt": plt,
        "matplotlib": plt,
        "pd": __import__('pandas'),
        "numpy": __import__('numpy'),
        "np": __import__('numpy')
    }
    if extra_globals:
        global_vars.update(extra_globals)
    
    try:
        # Count figures before execution
        figures_before = len(plt.get_fignums())
        
        # Add a comment to help GPT understand the context
        code_with_context = f"# DataFrame 'df' is already loaded with your data\n# Shape: {df.shape}\n# Columns: {list(df.columns)}\n{code}"
        
        exec(code_with_context, global_vars, local_vars)
        
        # Check if any figures were created
        figures_after = len(plt.get_fignums())
        if figures_after > figures_before:
            local_vars['chart_created'] = True
        
        return local_vars
    except Exception as e:
        tb = traceback.format_exc()
        return {"error": str(e), "traceback": tb}
