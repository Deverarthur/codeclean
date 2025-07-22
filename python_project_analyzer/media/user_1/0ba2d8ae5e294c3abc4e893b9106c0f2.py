import ast
import os

def generate_pytest_tests_for_project(project_dir):
    results = []
    for root, _, files in os.walk(project_dir):
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                with open(file_path, 'r', encoding='utf-8') as f:
                    source = f.read()
                tree = ast.parse(source)
                test_cases = []
                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef) and not node.name.startswith('test_'):
                        test_name = f"test_{node.name}"
                        test_case = (
                            f"def {test_name}():\n"
                            f"    # TODO: Implémenter un test pour {node.name}\n"
                            f"    assert True\n"
                        )
                        test_cases.append(test_case)
                if test_cases:
                    results.append({
                        'filename': file,
                        'test_cases': test_cases,
                    })
    return results