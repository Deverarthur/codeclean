import os
import ast

def generate_tests_report(project_path):
    """
    Génère des tests automatiques Pytest à partir des fichiers Python dans le projet.
    - Pour chaque fonction, un test basique est généré.
    - Si `urls.py` est détecté, des tests Django pour les vues sont générés.
    """
    test_code = "# Tests générés automatiquement avec pytest\n"
    test_code += "import pytest\n\n"

    urls_found = False
    view_names = []

    for filename in os.listdir(project_path):
        if not filename.endswith(".py"):
            continue

        filepath = os.path.join(project_path, filename)

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                source = f.read()
                tree = ast.parse(source, filename=filename)
        except Exception:
            continue  # Ignore les fichiers avec erreur

        module_name = os.path.splitext(filename)[0]
        functions = [n for n in tree.body if isinstance(n, ast.FunctionDef)]

        for func in functions:
            func_name = func.name
            args = [a.arg for a in func.args.args if a.arg != 'self']
            dummy_args = ", ".join(["1"] * len(args)) if args else ""

            test_code += f"def test_{func_name}():\n"
            test_code += f"    from {module_name} import {func_name}\n"
            test_code += f"    result = {func_name}({dummy_args})\n"
            test_code += f"    assert result is not None  # TODO: adapter cette assertion\n\n"

        # Si c'est urls.py : extraire les noms des vues (name="...") si possible
        if filename == "urls.py":
            urls_found = True
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    func = node.func
                    if (
                        (isinstance(func, ast.Name) and func.id == "path") or
                        (isinstance(func, ast.Attribute) and func.attr == "path")
                    ):
                        name_arg = None
                        for keyword in node.keywords:
                            if keyword.arg == "name" and isinstance(keyword.value, ast.Str):
                                name_arg = keyword.value.s
                        if name_arg:
                            view_names.append(name_arg)

    # Génération de tests Django pour les vues si des noms sont disponibles
    if urls_found and view_names:
        test_code += "from django.urls import reverse\n\n"
        test_code += "@pytest.mark.django_db\n"
        test_code += "def test_django_views(client):\n"
        for view in view_names:
            test_code += f"    response = client.get(reverse('{view}'))\n"
            test_code += f"    assert response.status_code in [200, 302]  # 302 si login_required\n"
        test_code += "\n"

    return test_code
