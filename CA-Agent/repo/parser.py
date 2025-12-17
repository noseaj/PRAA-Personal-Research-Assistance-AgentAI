import ast
import os

def extract_functions(path):
    funcs = []

    for root, _, files in os.walk(path):
        for f in files:
            if not f.endswith(".py"):
                continue

            file_path = os.path.join(root, f)
            try:
                code = open(file_path, encoding="utf-8").read()
                tree = ast.parse(code)
            except Exception:
                continue

            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    funcs.append({
                        "file": file_path.replace(path, ""),
                        "name": node.name,
                        "source": ast.get_source_segment(code, node),
                    })

    return funcs
