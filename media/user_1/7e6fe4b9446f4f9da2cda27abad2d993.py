import os
import ast
import radon.raw as raw
import radon.complexity as cc
from pylint.lint import Run
from pylint.reporters.text import TextReporter
import subprocess
import json
import joblib
import pandas as pd
from collections import defaultdict
import openai
from tenacity import retry, stop_after_attempt, wait_exponential
import asyncio
from openai import AsyncOpenAI
import google.generativeai as genai

class SecurityAnalyzer:
    def __init__(self):
        self.report = {
            "project_name": "",
            "files_analyzed": 0,
            "files_with_issues": 0,
            "total_issues": 0,
            "detailed_report": defaultdict(list),
            "summary_metrics": {}
        }
        
        # Mots-clés pour détecter les problèmes
        self.sensitive_keywords = ["password", "secret", "token", "key", "api_key", "access_token", "secret_key"]
        self.encryption_functions = [
            "cryptography.fernet.Fernet", "hashlib.sha256", "hashlib.md5",
            "pycryptodome.Cipher", "pycryptodome.Encrypt", "pycryptodome.Decrypt"
        ]
        self.sql_keywords = ["execute", "executemany", "raw"]
        self.xss_keywords = ["render", "render_to_string", "HttpResponse"]
        
        # Dictionnaire de recommandations
        self.recommendations = {
            "complexite_cyclomatique": {
                "low": "La complexité cyclomatique est acceptable.",
                "medium": "Considérez de refactoriser les fonctions complexes pour améliorer la maintenabilité.",
                "high": "Refactorisez immédiatement ces fonctions très complexes. Divisez-les en sous-fonctions plus petites."
            },
            "nombre_branches": {
                "low": "Nombre de branches acceptable.",
                "medium": "Trop de branches peuvent rendre le code difficile à suivre. Considérez de simplifier la logique.",
                "high": "Le code a trop de branches, ce qui augmente le risque d'erreurs. Refactorisez pour réduire la complexité."
            },
            "profondeur_heritage": {
                "low": "Profondeur d'héritage raisonnable.",
                "medium": "Profondeur d'héritage modérée. Évitez d'aller plus profond pour maintenir la lisibilité.",
                "high": "Profondeur d'héritage excessive. Considérez d'utiliser la composition plutôt que l'héritage."
            },
            "longueur_fonctions": {
                "low": "Longueur de fonctions appropriée.",
                "medium": "Certaines fonctions sont trop longues. Essayez de les diviser en fonctions plus petites.",
                "high": "Fonctions extrêmement longues détectées. Refactorisez immédiatement pour améliorer la maintenabilité."
            },
            "violations_pylint": {
                "low": "Peu de violations de style détectées.",
                "medium": "Nombre modéré de violations de style. Améliorez la qualité du code.",
                "high": "Nombre élevé de violations de style. Effectuez une révision complète du code."
            }
        }

    def analyze_project(self, project_path):
        """Analyse complète du projet Python"""
        self.report["project_name"] = os.path.basename(project_path)
        
        # Initialisation des métriques globales
        metrics = {
            "complexite_cyclomatique": 0,
            "nombre_branches": 0,
            "nombre_classes": 0,
            "total_fonctions": 0,
            "total_lignes_fonctions": 0,
            "total_parametres": 0,
            "lignes_code_effectif": 0,
            "lignes_commentaires": 0,
            "violations_pylint": 0,
            "annotations_type": 0,
            "variables_sensibles": 0,
            "injections_sql": 0,
            "xss_potentiels": 0,
            "csrf_protection": 0,
            "dependances_vulnerables": 0,
            "api_key_exposure": 0,
            "encryption_usage": 0,
            "authorization_checks": 0,
            "decorators_used": 0,
            "http_endpoints": 0,
            "code_duplique": 0
        }
        
        heritage_analyzer = HeritageAnalyzer()

        # Parcours des fichiers du projet
        for root, _, files in os.walk(project_path):
            for filename in files:
                if filename.endswith(".py"):
                    filepath = os.path.join(root, filename)
                    self.report["files_analyzed"] += 1
                    file_issues = self.analyze_file(filepath, metrics, heritage_analyzer)
                    
                    if file_issues:
                        self.report["files_with_issues"] += 1
                        self.report["total_issues"] += len(file_issues)
                        self.report["detailed_report"][filepath].extend(file_issues)

        # Analyse des dépendances
        self.analyze_dependencies(project_path, metrics)
        
        # Calcul des métriques finales
        metrics["profondeur_heritage"] = max(heritage_analyzer.classes.values(), default=0)
        metrics["longueur_moyenne_fonctions"] = round((metrics["total_lignes_fonctions"] / metrics["total_fonctions"]) if metrics["total_fonctions"] > 0 else 0, 2)
        metrics["parametres_moyens_par_fonction"] = round((metrics["total_parametres"] / metrics["total_fonctions"]) if metrics["total_fonctions"] > 0 else 0, 2)
        
        # Ajout des recommandations basées sur les métriques
        self.add_metric_recommendations(metrics)
        
        self.report["summary_metrics"] = metrics
        return self.report

    def add_metric_recommendations(self, metrics):
        """Ajoute des recommandations basées sur les métriques globales"""
        metrics["recommendations"] = []
        
        # Complexité cyclomatique
        cc_score = metrics["complexite_cyclomatique"]
        if cc_score > 50:
            metrics["recommendations"].append({
                "metric": "complexite_cyclomatique",
                "value": cc_score,
                "severity": "high",
                "recommendation": self.recommendations["complexite_cyclomatique"]["high"]
            })
        elif cc_score > 30:
            metrics["recommendations"].append({
                "metric": "complexite_cyclomatique",
                "value": cc_score,
                "severity": "medium",
                "recommendation": self.recommendations["complexite_cyclomatique"]["medium"]
            })
        else:
            metrics["recommendations"].append({
                "metric": "complexite_cyclomatique",
                "value": cc_score,
                "severity": "low",
                "recommendation": self.recommendations["complexite_cyclomatique"]["low"]
            })
        
        # Nombre de branches
        branches = metrics["nombre_branches"]
        if branches > 40:
            metrics["recommendations"].append({
                "metric": "nombre_branches",
                "value": branches,
                "severity": "high",
                "recommendation": self.recommendations["nombre_branches"]["high"]
            })
        elif branches > 20:
            metrics["recommendations"].append({
                "metric": "nombre_branches",
                "value": branches,
                "severity": "medium",
                "recommendation": self.recommendations["nombre_branches"]["medium"]
            })
        else:
            metrics["recommendations"].append({
                "metric": "nombre_branches",
                "value": branches,
                "severity": "low",
                "recommendation": self.recommendations["nombre_branches"]["low"]
            })
        
        # Profondeur d'héritage
        inheritance_depth = metrics["profondeur_heritage"]
        if inheritance_depth > 4:
            metrics["recommendations"].append({
                "metric": "profondeur_heritage",
                "value": inheritance_depth,
                "severity": "high",
                "recommendation": self.recommendations["profondeur_heritage"]["high"]
            })
        elif inheritance_depth > 2:
            metrics["recommendations"].append({
                "metric": "profondeur_heritage",
                "value": inheritance_depth,
                "severity": "medium",
                "recommendation": self.recommendations["profondeur_heritage"]["medium"]
            })
        else:
            metrics["recommendations"].append({
                "metric": "profondeur_heritage",
                "value": inheritance_depth,
                "severity": "low",
                "recommendation": self.recommendations["profondeur_heritage"]["low"]
            })
        
        # Longueur des fonctions
        avg_func_length = metrics["longueur_moyenne_fonctions"]
        if avg_func_length > 30:
            metrics["recommendations"].append({
                "metric": "longueur_moyenne_fonctions",
                "value": avg_func_length,
                "severity": "high",
                "recommendation": "Les fonctions sont trop longues en moyenne. Essayez de respecter la règle des 20 lignes maximum par fonction."
            })
        elif avg_func_length > 20:
            metrics["recommendations"].append({
                "metric": "longueur_moyenne_fonctions",
                "value": avg_func_length,
                "severity": "medium",
                "recommendation": "Certaines fonctions sont trop longues. Considérez de les diviser en sous-fonctions."
            })
        
        # Violations Pylint
        pylint_violations = metrics["violations_pylint"]
        if pylint_violations > 50:
            metrics["recommendations"].append({
                "metric": "violations_pylint",
                "value": pylint_violations,
                "severity": "high",
                "recommendation": "Nombre élevé de violations de style. Effectuez une révision complète du code selon les standards PEP 8."
            })
        elif pylint_violations > 20:
            metrics["recommendations"].append({
                "metric": "violations_pylint",
                "value": pylint_violations,
                "severity": "medium",
                "recommendation": "Nombre modéré de violations de style. Améliorez la qualité du code en corrigeant ces problèmes."
            })
        
        # Variables sensibles
        if metrics["variables_sensibles"] > 0:
            metrics["recommendations"].append({
                "metric": "variables_sensibles",
                "value": metrics["variables_sensibles"],
                "severity": "high",
                "recommendation": f"{metrics['variables_sensibles']} variables sensibles détectées. Utilisez des variables d'environnement ou un gestionnaire de secrets comme Vault."
            })
        
        # Injections SQL
        if metrics["injections_sql"] > 0:
            metrics["recommendations"].append({
                "metric": "injections_sql",
                "value": metrics["injections_sql"],
                "severity": "critical",
                "recommendation": f"{metrics['injections_sql']} injections SQL potentielles détectées. Utilisez toujours des requêtes paramétrées ou un ORM."
            })
        
        # XSS
        if metrics["xss_potentiels"] > 0:
            metrics["recommendations"].append({
                "metric": "xss_potentiels",
                "value": metrics["xss_potentiels"],
                "severity": "high",
                "recommendation": f"{metrics['xss_potentiels']} vulnérabilités XSS potentielles. Échappez toujours les entrées utilisateur avec des filtres appropriés."
            })

    def analyze_file(self, filepath, metrics, heritage_analyzer):
        """Analyse un fichier Python spécifique"""
        issues = []
        
        with open(filepath, 'r', encoding='utf-8') as f:
            try:
                code = f.read()
                lines = code.split('\n')
                
                # Analyse avec Radon
                self.analyze_with_radon(code, metrics)
                
                # Analyse avec AST
                tree = ast.parse(code)
                heritage_analyzer.visit(tree)
                
                # Analyse des noeuds AST
                for node in ast.walk(tree):
                    issues.extend(self.check_sensitive_variables(node, lines, filepath))
                    issues.extend(self.check_sql_injections(node, lines, filepath))
                    issues.extend(self.check_xss_vulnerabilities(node, lines, filepath))
                    issues.extend(self.check_encryption_usage(node, lines, filepath))
                    issues.extend(self.check_csrf_protection(node, lines, filepath))
                    issues.extend(self.check_authorization(node, lines, filepath))
                    issues.extend(self.check_http_endpoints(node, lines, filepath))
                    
                    # Comptage des éléments structurels
                    self.count_structural_elements(node, metrics)
                
                # Analyse avec Pylint
                metrics["violations_pylint"] += self.run_pylint_analysis(filepath)
                
                # Analyse du code brut
                self.analyze_raw_code(code, metrics)
                
            except Exception as e:
                issues.append({
                    "line": "N/A",
                    "type": "Erreur d'analyse",
                    "message": f"Impossible d'analyser le fichier: {str(e)}",
                    "severity": "high"
                })
        
        return issues

    def analyze_with_radon(self, code, metrics):
        """Analyse avec Radon pour la complexité cyclomatique"""
        results = cc.cc_visit(code)
        for result in results:
            metrics["complexite_cyclomatique"] += result.complexity
            metrics["nombre_branches"] += result.complexity - 1

    def count_structural_elements(self, node, metrics):
        """Compte les éléments structurels du code"""
        if isinstance(node, ast.ClassDef):
            metrics["nombre_classes"] += 1
        elif isinstance(node, ast.FunctionDef):
            metrics["total_fonctions"] += 1
            metrics["total_lignes_fonctions"] += (node.end_lineno - node.lineno + 1) if hasattr(node, 'end_lineno') else 1
            metrics["total_parametres"] += len(node.args.args)
            
            # Annotations de type
            for arg in node.args.args:
                if arg.annotation:
                    metrics["annotations_type"] += 1
            if node.returns:
                metrics["annotations_type"] += 1
            
            # Décoration
            metrics["decorators_used"] += len(node.decorator_list)
            
        elif isinstance(node, ast.AnnAssign):
            metrics["annotations_type"] += 1

    def check_sensitive_variables(self, node, lines, filepath):
        """Détecte les variables sensibles"""
        issues = []
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    var_name = target.id.lower()
                    if any(kw in var_name for kw in self.sensitive_keywords):
                        line_no = node.lineno
                        line_content = lines[line_no-1].strip()
                        
                        issue = {
                            "line": line_no,
                            "type": "Variable sensible",
                            "message": f"Variable sensible détectée: '{var_name}'",
                            "severity": "high",
                            "recommendation": "Utilisez des variables d'environnement ou un gestionnaire de secrets.",
                            "code_excerpt": line_content
                        }
                        
                        if "api_key" in var_name or "access_token" in var_name:
                            issue["subtype"] = "Exposition de clé API"
                            issue["recommendation"] += " Considérez l'utilisation d'un service de gestion des secrets."
                        
                        issues.append(issue)
        return issues

    def check_sql_injections(self, node, lines, filepath):
        """Détecte les injections SQL potentielles"""
        issues = []
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr in self.sql_keywords:
                for arg in node.args:
                    if isinstance(arg, (ast.BinOp, ast.Name)):
                        line_no = node.lineno
                        line_content = lines[line_no-1].strip()
                        
                        issues.append({
                            "line": line_no,
                            "type": "Injection SQL potentielle",
                            "message": "Construction dynamique de requête SQL détectée",
                            "severity": "critical",
                            "recommendation": "Utilisez des requêtes paramétrées ou un ORM.",
                            "code_excerpt": line_content
                        })
        return issues

    def check_xss_vulnerabilities(self, node, lines, filepath):
        """Détecte les vulnérabilités XSS potentielles"""
        issues = []
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr in self.xss_keywords:
                for arg in node.args:
                    if isinstance(arg, ast.Name):
                        line_no = node.lineno
                        line_content = lines[line_no-1].strip()
                        
                        issues.append({
                            "line": line_no,
                            "type": "XSS potentiel",
                            "message": "Données non échappées passées à une fonction de rendu",
                            "severity": "high",
                            "recommendation": "Échappez toujours les entrées utilisateur avec des filtres appropriés.",
                            "code_excerpt": line_content
                        })
        return issues

    def check_encryption_usage(self, node, lines, filepath):
        """Vérifie l'utilisation de fonctions de chiffrement"""
        issues = []
        if isinstance(node, ast.Call):
            func_name = ""
            if isinstance(node.func, ast.Attribute):
                if isinstance(node.func.value, ast.Name):
                    func_name = f"{node.func.value.id}.{node.func.attr}"
                else:
                    func_name = node.func.attr
            elif isinstance(node.func, ast.Name):
                func_name = node.func.id
            
            if func_name in self.encryption_functions:
                line_no = node.lineno
                line_content = lines[line_no-1].strip()
                
                issues.append({
                    "line": line_no,
                    "type": "Utilisation de chiffrement",
                    "message": f"Fonction de chiffrement utilisée: {func_name}",
                    "severity": "info",
                    "recommendation": "Vérifiez que l'implémentation est correcte et utilise des algorithmes forts.",
                    "code_excerpt": line_content
                })
        return issues

    def check_csrf_protection(self, node, lines, filepath):
        """Vérifie la protection CSRF"""
        issues = []
        if isinstance(node, ast.FunctionDef):
            is_protected = False
            for decorator in node.decorator_list:
                if (isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Name) and decorator.func.id == "csrf_protect"):
                    is_protected = True
                elif isinstance(decorator, ast.Name) and decorator.id == "csrf_protect":
                    is_protected = True
            
            if not is_protected and any(isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr in ["post", "put", "delete"] for n in ast.walk(node)):
                issues.append({
                    "line": node.lineno,
                    "type": "Protection CSRF manquante",
                    "message": "Point de terminaison modifiant l'état sans protection CSRF",
                    "severity": "high",
                    "recommendation": "Ajoutez @csrf_protect ou utilisez @require_POST avec csrf_token.",
                    "code_excerpt": lines[node.lineno-1].strip()
                })
        return issues

    def check_authorization(self, node, lines, filepath):
        """Vérifie les contrôles d'autorisation"""
        issues = []
        if isinstance(node, ast.If):
            if isinstance(node.test, ast.Call) and isinstance(node.test.func, ast.Attribute) and node.test.func.attr == "has_permission":
                return issues
            
            # Vérifie les accès à des objets sensibles sans contrôle
            for n in ast.walk(node):
                if isinstance(n, ast.Attribute) and n.attr in ["user", "request"]:
                    if not self.has_authorization_check(node):
                        issues.append({
                            "line": node.lineno,
                            "type": "Contrôle d'autorisation manquant",
                            "message": "Accès à des données sensibles sans vérification d'autorisation explicite",
                            "severity": "high",
                            "recommendation": "Implémentez des vérifications d'autorisation explicites avant d'accéder aux données.",
                            "code_excerpt": lines[node.lineno-1].strip()
                        })
                    break
        return issues

    def has_authorization_check(self, node):
        """Vérifie si le nœud contient une vérification d'autorisation"""
        for n in ast.walk(node):
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute):
                if n.func.attr in ["has_permission", "has_role", "is_authenticated"]:
                    return True
        return False

    def check_http_endpoints(self, node, lines, filepath):
        """Détecte les points de terminaison HTTP"""
        issues = []
        if isinstance(node, ast.FunctionDef):
            for decorator in node.decorator_list:
                if isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Attribute):
                    if decorator.func.attr in ["get", "post", "put", "delete", "patch"]:
                        # Vérifie les paramètres de requête non validés
                        for arg in node.args.args:
                            if isinstance(arg, ast.arg) and arg.arg in ["request", "query_params"]:
                                if not self.has_input_validation(node):
                                    issues.append({
                                        "line": node.lineno,
                                        "type": "Validation d'entrée manquante",
                                        "message": f"Point de terminaison {decorator.func.attr.upper()} sans validation des entrées",
                                        "severity": "medium",
                                        "recommendation": "Validez et nettoyez toutes les entrées utilisateur.",
                                        "code_excerpt": lines[node.lineno-1].strip()
                                    })
        return issues

    def has_input_validation(self, node):
        """Vérifie si le nœud contient une validation d'entrée"""
        for n in ast.walk(node):
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Name):
                if n.func.id in ["validate", "clean", "sanitize"]:
                    return True
        return False

    def run_pylint_analysis(self, filepath):
        """Exécute Pylint sur le fichier"""
        class CustomReporter(TextReporter):
            def __init__(self):
                super().__init__(output=None)
                self.violations = []
            
            def handle_message(self, msg):
                self.violations.append(msg)
        
        reporter = CustomReporter()
        Run([filepath], reporter=reporter, exit=False)
        return len(reporter.violations)

    def analyze_raw_code(self, code, metrics):
        """Analyse les lignes de code brutes"""
        analysis = raw.analyze(code)
        metrics["lignes_code_effectif"] += analysis.loc
        metrics["lignes_commentaires"] += analysis.comments

    def analyze_dependencies(self, project_path, metrics):
        """Analyse les dépendances vulnérables"""
        try:
            result = subprocess.run(['safety', 'check', '--json'], cwd=project_path, capture_output=True, text=True)
            if result.returncode in (0, 1):  # 0 = pas de vulnérabilités, 1 = vulnérabilités trouvées
                vulns = json.loads(result.stdout) if result.stdout else []
                metrics["dependances_vulnerables"] = len(vulns)
                
                for vuln in vulns:
                    for filepath in self.report["detailed_report"]:
                        self.report["detailed_report"][filepath].append({
                            "line": "N/A",
                            "type": "Dépendance vulnérable",
                            "message": f"{vuln.get('package_name', '')} {vuln.get('vulnerable_spec', '')}: {vuln.get('advisory', '')}",
                            "severity": "high",
                            "recommendation": f"Mettez à jour vers {vuln.get('analyzed_version', '')} ou plus récent."
                        })
        except Exception as e:
            print(f"Erreur lors de l'analyse des dépendances: {e}")

    def generate_report(self):
        """Génère un rapport détaillé des analyses avec recommandations"""
        report_lines = [
            f"*** Rapport d'Analyse de Sécurité et Qualité ***",
            f"Projet: {self.report['project_name']}",
            f"Fichiers analysés: {self.report['files_analyzed']}",
            f"Fichiers avec problèmes: {self.report['files_with_issues']}",
            f"Total des problèmes détectés: {self.report['total_issues']}\n",
            "=== Recommandations Globales ==="
        ]
        
        # Ajout des recommandations basées sur les métriques
        metrics = self.report["summary_metrics"]
        if "recommendations" in metrics:
            for rec in metrics["recommendations"]:
                report_lines.append(f"\n- [{rec['severity'].upper()}] {rec['metric']} = {rec['value']}")
                report_lines.append(f"  Recommandation: {rec['recommendation']}")
        
        # Détails par fichier
        report_lines.append("\n=== Détails par Fichier ===")
        for filepath, issues in self.report["detailed_report"].items():
            report_lines.append(f"\nFichier: {filepath}")
            
            if not issues:
                report_lines.append("  - Statut: Aucun problème détecté")
                continue
            
            report_lines.append("  - Problèmes détectés:")
            
            for issue in issues:
                report_lines.append(f"    * Ligne {issue['line']}: [{issue['type']}] {issue['message']}")
                report_lines.append(f"      Gravité: {issue['severity'].upper()}")
                report_lines.append(f"      Recommandation: {issue['recommendation']}")
                if "code_excerpt" in issue:
                    report_lines.append(f"      Code: {issue['code_excerpt']}")
        
        # Résumé des métriques
        report_lines.append("\n=== Métriques Globales ===")
        report_lines.append(f"Complexité cyclomatique totale: {metrics['complexite_cyclomatique']}")
        report_lines.append(f"Nombre de branches: {metrics['nombre_branches']}")
        report_lines.append(f"Profondeur d'héritage max: {metrics['profondeur_heritage']}")
        report_lines.append(f"Nombre de classes: {metrics['nombre_classes']}")
        report_lines.append(f"Total fonctions: {metrics['total_fonctions']}")
        report_lines.append(f"Longueur moyenne des fonctions: {metrics['longueur_moyenne_fonctions']} lignes")
        report_lines.append(f"Paramètres moyens par fonction: {metrics['parametres_moyens_par_fonction']}")
        report_lines.append(f"Lignes de code effectif: {metrics['lignes_code_effectif']}")
        report_lines.append(f"Lignes de commentaires: {metrics['lignes_commentaires']}")
        report_lines.append(f"Violations Pylint: {metrics['violations_pylint']}")
        report_lines.append(f"Dépendances vulnérables: {metrics['dependances_vulnerables']}")
        report_lines.append(f"Variables sensibles: {metrics['variables_sensibles']}")
        report_lines.append(f"Injections SQL potentielles: {metrics['injections_sql']}")
        report_lines.append(f"XSS potentiels: {metrics['xss_potentiels']}")
        
        return "\n".join(report_lines)
    

class LLMAnalyzer:
    def __init__(self, api_key):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-2.0-flash')
        self.prompt_templates = {
            "security_issue": "Analyse vulnérabilité en 1 ligne: {issue_type}",
            "code_quality": "Analyse qualité en 1 ligne: {metric}"
        }

    @retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, min=2, max=5))
    async def get_llm_analysis(self, prompt):
        try:
            response = await self.model.generate_content(prompt[:150])  # Limite la taille du prompt
            return response.text[:100]  # Retourne max 100 caractères
        except Exception:
            return "Erreur API - réponse tronquée"


async def generate_llm_report(analysis_report, api_key):
    """Génère un rapport enrichi avec OpenAI"""
    llm = LLMAnalyzer(api_key)
    enhanced_report = {
        "security_analysis": await enhance_security_findings(analysis_report, llm),
        #"quality_analysis": await enhance_quality_metrics(analysis_report["summary_metrics"], llm),
        #"executive_summary": await generate_executive_summary(analysis_report, llm)
    }
    return format_llm_report(enhanced_report)

async def enhance_security_findings(analysis_report, llm):
    findings = []
    for filepath, issues in analysis_report["detailed_report"].items():
        for issue in issues[:2]:  # Limite à 2 problèmes par fichier
            prompt = f"Problème {issue['type']} - solution en 5 mots max"
            findings.append(await llm.get_llm_analysis(prompt))
    return findings[:5]  # Retourne max 5 findings

async def enhance_quality_metrics(metrics, llm):
    """Améliore l'analyse des métriques de qualité"""
    quality_metrics = [
        ("complexite_cyclomatique", 30),
        ("longueur_moyenne_fonctions", 20),
        ("profondeur_heritage", 3),
        ("violations_pylint", 20)
    ]
    
    enhanced_metrics = []
    
    for metric, threshold in quality_metrics:
        if metrics[metric] > threshold:
            prompt = llm.prompt_templates["code_quality"].format(
                metric=metric,
                value=metrics[metric],
                threshold=threshold
            )
            
            analysis = await llm.get_llm_analysis(prompt)
            if analysis:
                enhanced_metrics.append({
                    "metric": metric,
                    "value": metrics[metric],
                    "threshold": threshold,
                    "llm_analysis": analysis
                })
    
    return enhanced_metrics

async def generate_executive_summary(analysis_report, llm):
    prompt = "Résume en 1 ligne: "
    prompt += f"{analysis_report['files_analyzed']} fichiers, "
    prompt += f"{analysis_report['total_issues']} problèmes"
    return await llm.get_llm_analysis(prompt)


def extract_llm_recommendations(analysis_text):
    """Extrait les recommandations du texte d'analyse"""
    # Implémentation simplifiée - pourrait utiliser une regex plus sophistiquée
    parts = analysis_text.split("Solution recommandée:")
    return parts[-1].split("Références")[0] if len(parts) > 1 else analysis_text

def format_llm_report(enhanced_report):
    """Formate le rapport final"""
    report = ["# Rapport d'Analyse Amélioré par IA\n"]
    
    # Résumé exécutif
    report.append("## Résumé Exécutif\n")
    report.append(enhanced_report["executive_summary"] or "Non disponible")
    
    # Analyse de sécurité
    report.append("\n## Analyse Approfondie des Vulnérabilités\n")
    for finding in enhanced_report["security_analysis"]:
        report.append(f"### {finding['type']} (Ligne {finding['line']})")
        report.append(f"**Fichier**: {finding['file']}")
        report.append(f"**Analyse IA**:\n{finding['llm_analysis']}")
        report.append(f"**Recommandation**: {finding['recommendation']}")
        report.append("")
    
    # Qualité de code
    report.append("\n## Analyse des Métriques de Qualité\n")
    for metric in enhanced_report["quality_analysis"]:
        report.append(f"### {metric['metric']} (Valeur: {metric['value']} > Seuil: {metric['threshold']})")
        report.append(f"**Analyse IA**:\n{metric['llm_analysis']}")
        report.append("")
    
    return "\n".join(report)

class HeritageAnalyzer(ast.NodeVisitor):
    """Analyse la profondeur d'héritage des classes"""
    def __init__(self):
        self.classes = {}

    def visit_ClassDef(self, node):
        class_name = node.name
        base_classes = [base.id for base in node.bases if isinstance(base, ast.Name)]
        
        if not base_classes:
            depth = 1
        else:
            max_parent_depth = max(self.classes.get(base, 1) for base in base_classes)
            depth = max_parent_depth + 1
        
        self.classes[class_name] = depth
        self.generic_visit(node)


def generate_llm_report1(analysis_report):
    """Génère un rapport enrichi avec des explications détaillées et des recommandations personnalisées"""
    
    # Structure du rapport enrichi
    enhanced_report = {
        "overview": "",
        "security_analysis": [],
        "code_quality_analysis": [],
        "critical_issues": [],
        "detailed_recommendations": [],
        "action_plan": []
    }
    
    # 1. Générer un aperçu global
    metrics = analysis_report["summary_metrics"]
    enhanced_report["overview"] = generate_project_overview(analysis_report, metrics)
    
    # 2. Analyse de sécurité détaillée
    enhanced_report["security_analysis"] = generate_security_analysis(analysis_report, metrics)
    
    # 3. Analyse de qualité de code
    enhanced_report["code_quality_analysis"] = generate_code_quality_analysis(metrics)
    
    # 4. Problèmes critiques
    enhanced_report["critical_issues"] = identify_critical_issues(analysis_report)
    
    # 5. Recommandations détaillées
    enhanced_report["detailed_recommendations"] = generate_detailed_recommendations(analysis_report)
    
    # 6. Plan d'action priorisé
    enhanced_report["action_plan"] = generate_action_plan(analysis_report)
    
    return format_llm_report(enhanced_report)

def generate_project_overview(analysis_report, metrics):
    """Génère un résumé global du projet"""
    overview = [
        f"## Aperçu du Projet: {analysis_report['project_name']}",
        f"- **Fichiers analysés**: {analysis_report['files_analyzed']}",
        f"- **Fichiers avec problèmes**: {analysis_report['files_with_issues']} ({analysis_report['files_with_issues']/analysis_report['files_analyzed']*100:.1f}%)",
        f"- **Problèmes totaux**: {analysis_report['total_issues']}",
        "",
        "### Évaluation Globale:",
        get_overall_assessment(metrics),
        "",
        "### Points Forts:",
        "- " + identify_strengths(metrics),
        "",
        "### Principaux Domaines à Améliorer:",
        "- " + identify_main_improvement_areas(metrics)
    ]
    
    return "\n".join(overview)

def get_overall_assessment(metrics):
    """Donne une évaluation globale basée sur les métriques"""
    critical_issues = metrics["injections_sql"] + metrics["xss_potentiels"] + metrics["dependances_vulnerables"]
    
    if critical_issues > 5:
        return "🔴 Projet à haut risque - Plusieurs vulnérabilités critiques détectées nécessitant une attention immédiate."
    elif critical_issues > 0:
        return "🟠 Projet à risque modéré - Certaines vulnérabilités critiques présentes nécessitant correction."
    elif metrics["variables_sensibles"] > 0 or metrics["complexite_cyclomatique"] > 50:
        return "🟡 Projet avec problèmes importants - Pas de vulnérabilités critiques mais des problèmes de sécurité ou de qualité notables."
    else:
        return "🟢 Projet relativement sain - Aucune vulnérabilité critique détectée, quelques améliorations possibles."

def identify_strengths(metrics):
    """Identifie les points forts du projet"""
    strengths = []
    
    if metrics["injections_sql"] == 0:
        strengths.append("Aucune injection SQL détectée")
    if metrics["xss_potentiels"] == 0:
        strengths.append("Aucune vulnérabilité XSS détectée")
    if metrics["dependances_vulnerables"] == 0:
        strengths.append("Aucune dépendance vulnérable identifiée")
    if metrics["complexite_cyclomatique"] < 30:
        strengths.append("Complexité cyclomatique globale raisonnable")
    if metrics["violations_pylint"] < 20:
        strengths.append("Bon respect des standards de codage (peu de violations Pylint)")
    
    return "\n- ".join(strengths) if strengths else "Aucun point fort particulier identifié"

def identify_main_improvement_areas(metrics):
    """Identifie les principaux domaines à améliorer"""
    improvements = []
    
    if metrics["injections_sql"] > 0:
        improvements.append(f"{metrics['injections_sql']} injections SQL potentielles")
    if metrics["xss_potentiels"] > 0:
        improvements.append(f"{metrics['xss_potentiels']} vulnérabilités XSS potentielles")
    if metrics["variables_sensibles"] > 0:
        improvements.append(f"{metrics['variables_sensibles']} variables sensibles exposées")
    if metrics["complexite_cyclomatique"] > 50:
        improvements.append("Complexité cyclomatique élevée")
    if metrics["violations_pylint"] > 50:
        improvements.append("Nombre important de violations de style")
    
    return "\n- ".join(improvements) if improvements else "Le projet est globalement bien structuré"

def generate_security_analysis(analysis_report, metrics):
    """Génère une analyse de sécurité détaillée"""
    security_analysis = []
    
    # 1. Vulnérabilités critiques
    if metrics["injections_sql"] > 0:
        security_analysis.append({
            "category": "Sécurité",
            "issue": "Injection SQL",
            "count": metrics["injections_sql"],
            "severity": "Critical",
            "description": "Les injections SQL permettent à des attaquants d'exécuter des commandes SQL malveillantes sur votre base de données.",
            "recommendations": [
                "Utilisez toujours des requêtes paramétrées ou un ORM comme Django ORM ou SQLAlchemy.",
                "Évitez de concaténer directement des entrées utilisateur dans des requêtes SQL.",
                "Implémentez le principe du moindre privilège pour les accès base de données."
            ],
            "resources": [
                "OWASP SQL Injection: https://owasp.org/www-community/attacks/SQL_Injection",
                "Django Database Security: https://docs.djangoproject.com/en/stable/topics/security/#sql-injection-protection"
            ]
        })
    
    if metrics["xss_potentiels"] > 0:
        security_analysis.append({
            "category": "Sécurité",
            "issue": "Cross-Site Scripting (XSS)",
            "count": metrics["xss_potentiels"],
            "severity": "High",
            "description": "Les vulnérabilités XSS permettent à des attaquants d'injecter du code JavaScript malveillant qui sera exécuté dans le navigateur des utilisateurs.",
            "recommendations": [
                "Échappez toujours les données non fiables avec les filtres appropriés (escape, safe, etc.).",
                "Utilisez le système de templates qui échappe automatiquement les variables.",
                "Implémentez une politique de sécurité de contenu (CSP) pour limiter l'exécution de scripts."
            ],
            "resources": [
                "OWASP XSS: https://owasp.org/www-community/attacks/xss/",
                "Django XSS Protection: https://docs.djangoproject.com/en/stable/topics/security/#cross-site-scripting-xss-protection"
            ]
        })
    
    # 2. Problèmes de sécurité courants
    if metrics["variables_sensibles"] > 0:
        security_analysis.append({
            "category": "Sécurité",
            "issue": "Exposition de données sensibles",
            "count": metrics["variables_sensibles"],
            "severity": "High",
            "description": "Des variables contenant des informations sensibles (mots de passe, clés API) sont codées en dur dans le code source.",
            "recommendations": [
                "Utilisez des variables d'environnement pour stocker les informations sensibles.",
                "Considérez l'utilisation d'un gestionnaire de secrets comme HashiCorp Vault ou AWS Secrets Manager.",
                "Ne jamais commettre de secrets dans le contrôle de version (ajoutez-les à .gitignore)."
            ],
            "resources": [
                "Django Secret Key Management: https://docs.djangoproject.com/en/stable/topics/settings/#secret-key",
                "12 Factor App Config: https://12factor.net/config"
            ]
        })
    
    if metrics["csrf_protection"] > 0:
        security_analysis.append({
            "category": "Sécurité",
            "issue": "Protection CSRF manquante",
            "count": metrics["csrf_protection"],
            "severity": "High",
            "description": "Des endpoints modifiant l'état ne sont pas protégés contre les attaques CSRF (Cross-Site Request Forgery).",
            "recommendations": [
                "Ajoutez le décorateur @csrf_protect à toutes les vues qui modifient l'état.",
                "Pour les API REST, utilisez des tokens CSRF ou envisagez d'autres mécanismes d'authentification.",
                "Vérifiez que le middleware CSRF est activé dans les paramètres Django."
            ],
            "resources": [
                "Django CSRF Protection: https://docs.djangoproject.com/en/stable/ref/csrf/",
                "OWASP CSRF: https://owasp.org/www-community/attacks/csrf"
            ]
        })
    
    # 3. Dépendances vulnérables
    if metrics["dependances_vulnerables"] > 0:
        security_analysis.append({
            "category": "Dépendances",
            "issue": "Dépendances vulnérables",
            "count": metrics["dependances_vulnerables"],
            "severity": "Critical",
            "description": "Certaines dépendances utilisées contiennent des vulnérabilités connues qui pourraient être exploitées.",
            "recommendations": [
                "Mettez à jour immédiatement les dépendances vulnérables vers leurs dernières versions stables.",
                "Utilisez des outils comme safety ou dependabot pour surveiller les vulnérabilités.",
                "Revoyez régulièrement vos dépendances et supprimez celles qui ne sont pas utilisées."
            ],
            "resources": [
                "PyUp Safety: https://pyup.io/safety/",
                "Django Security Releases: https://www.djangoproject.com/weblog/"
            ]
        })
    
    return security_analysis

def generate_code_quality_analysis(metrics):
    """Génère une analyse de la qualité du code"""
    quality_analysis = []
    
    # 1. Complexité du code
    if metrics["complexite_cyclomatique"] > 50:
        quality_analysis.append({
            "category": "Qualité",
            "issue": "Complexité cyclomatique élevée",
            "value": metrics["complexite_cyclomatique"],
            "severity": "High",
            "description": "Une complexité cyclomatique élevée indique un code difficile à maintenir et à tester, avec de nombreux chemins d'exécution possibles.",
            "recommendations": [
                "Refactorisez les fonctions les plus complexes (score > 15) en les divisant en sous-fonctions.",
                "Appliquez le principe de responsabilité unique - chaque fonction devrait faire une seule chose.",
                "Considérez l'utilisation de design patterns pour simplifier la logique complexe."
            ],
            "resources": [
                "Refactoring Guru: https://refactoring.guru/",
                "Cyclomatic Complexity: https://en.wikipedia.org/wiki/Cyclomatic_complexity"
            ]
        })
    
    # 2. Longueur des fonctions
    if metrics["longueur_moyenne_fonctions"] > 20:
        quality_analysis.append({
            "category": "Qualité",
            "issue": "Fonctions trop longues",
            "value": f"{metrics['longueur_moyenne_fonctions']} lignes en moyenne",
            "severity": "Medium",
            "description": "Les fonctions longues sont difficiles à comprendre, tester et maintenir. La règle générale est de ne pas dépasser 20 lignes par fonction.",
            "recommendations": [
                "Divisez les fonctions longues en plusieurs petites fonctions avec des responsabilités claires.",
                "Extrayez les blocs logiques en méthodes séparées.",
                "Utilisez des fonctions d'ordre supérieur pour simplifier les flux complexes."
            ],
            "resources": [
                "Clean Code Functions: https://github.com/zedr/clean-code-python#functions",
                "Refactoring Long Methods: https://refactoring.com/catalog/extractMethod.html"
            ]
        })
    
    # 3. Style de code
    if metrics["violations_pylint"] > 20:
        quality_analysis.append({
            "category": "Qualité",
            "issue": "Violations de style de code",
            "value": metrics["violations_pylint"],
            "severity": "Medium",
            "description": "De nombreuses violations des conventions PEP 8 rendent le code moins lisible et plus difficile à maintenir.",
            "recommendations": [
                "Utilisez un formateur de code comme black ou autopep8 pour corriger automatiquement les problèmes de style.",
                "Configurez votre IDE pour vérifier le style de code en temps réel.",
                "Mettez en place des hooks git pour vérifier le style avant les commits."
            ],
            "resources": [
                "PEP 8 Style Guide: https://peps.python.org/pep-0008/",
                "Black Formatter: https://github.com/psf/black"
            ]
        })
    
    # 4. Héritage
    if metrics["profondeur_heritage"] > 3:
        quality_analysis.append({
            "category": "Design",
            "issue": "Profondeur d'héritage excessive",
            "value": metrics["profondeur_heritage"],
            "severity": "Medium",
            "description": "Une hiérarchie d'héritage profonde rend le code rigide et difficile à modifier. La composition est souvent préférable à l'héritage.",
            "recommendations": [
                "Remplacez l'héritage par la composition lorsque possible.",
                "Limitez la profondeur d'héritage à 2-3 niveaux maximum.",
                "Considérez l'utilisation de mixins pour le partage de fonctionnalités."
            ],
            "resources": [
                "Composition over Inheritance: https://en.wikipedia.org/wiki/Composition_over_inheritance",
                "Python Mixins: https://stackoverflow.com/questions/533631/what-is-a-mixin-and-why-are-they-useful"
            ]
        })
    
    return quality_analysis

def identify_critical_issues(analysis_report):
    """Identifie et classe les problèmes critiques par priorité"""
    critical_issues = []
    
    # Parcours des problèmes détectés dans chaque fichier
    for filepath, issues in analysis_report["detailed_report"].items():
        for issue in issues:
            if issue["severity"] in ["critical", "high"]:
                critical_issues.append({
                    "file": filepath,
                    "line": issue["line"],
                    "type": issue["type"],
                    "severity": issue["severity"],
                    "description": issue["message"],
                    "recommendation": issue.get("recommendation", "")
                })
    
    # Tri par sévérité (critical d'abord, puis high)
    critical_issues.sort(key=lambda x: 0 if x["severity"] == "critical" else 1)
    
    return critical_issues

def generate_detailed_recommendations(analysis_report):
    """Génère des recommandations détaillées pour chaque type de problème"""
    recommendations = []
    metrics = analysis_report["summary_metrics"]
    
    # 1. Recommandations de sécurité
    if metrics["injections_sql"] > 0:
        recommendations.append({
            "category": "Sécurité",
            "priority": "Critical",
            "action": "Corriger les injections SQL potentielles",
            "steps": [
                "Identifier toutes les requêtes SQL construites dynamiquement",
                "Remplacer par des requêtes paramétrées ou utiliser l'ORM",
                "Tester les corrections avec des entrées malveillantes simulées"
            ],
            "estimated_time": "2-4 heures par occurrence"
        })
    
    if metrics["xss_potentiels"] > 0:
        recommendations.append({
            "category": "Sécurité",
            "priority": "High",
            "action": "Protéger contre les attaques XSS",
            "steps": [
                "Échapper systématiquement les données utilisateur dans les templates",
                "Utiliser mark_safe uniquement lorsque nécessaire et avec validation",
                "Implémenter une politique de sécurité de contenu (CSP)"
            ],
            "estimated_time": "1-2 heures par occurrence"
        })
    
    # 2. Recommandations de qualité
    if metrics["complexite_cyclomatique"] > 50:
        recommendations.append({
            "category": "Qualité",
            "priority": "High",
            "action": "Réduire la complexité cyclomatique",
            "steps": [
                "Identifier les fonctions avec une complexité > 15",
                "Refactoriser en petites fonctions avec une seule responsabilité",
                "Utiliser des design patterns comme Stratégie ou État pour les logiques complexes"
            ],
            "estimated_time": "30 minutes par fonction"
        })
    
    if metrics["violations_pylint"] > 20:
        recommendations.append({
            "category": "Qualité",
            "priority": "Medium",
            "action": "Améliorer la conformité PEP 8",
            "steps": [
                "Exécuter black ou autopep8 sur le codebase",
                "Configurer le linting dans le CI/CD",
                "Former l'équipe aux standards PEP 8"
            ],
            "estimated_time": "2-4 heures pour l'ensemble du projet"
        })
    
    return recommendations

def generate_action_plan(analysis_report):
    """Génère un plan d'action priorisé"""
    action_plan = []
    metrics = analysis_report["summary_metrics"]
    
    # 1. Actions critiques (sécurité)
    if metrics["injections_sql"] > 0 or metrics["xss_potentiels"] > 0:
        action_plan.append({
            "phase": "Immédiat",
            "actions": [
                "Corriger toutes les injections SQL potentielles",
                "Échapper les sorties pour prévenir les XSS",
                "Mettre à jour les dépendances vulnérables"
            ],
            "owner": "Lead Developer",
            "timeline": "1-3 jours"
        })
    
    # 2. Actions importantes
    action_plan.append({
        "phase": "Court terme",
        "actions": [
            "Sécuriser les variables sensibles (variables d'environnement)",
            "Implémenter les protections CSRF manquantes",
            "Refactoriser les fonctions trop complexes"
        ],
        "owner": "Équipe de développement",
        "timeline": "1-2 semaines"
    })
    
    # 3. Actions d'amélioration continue
    action_plan.append({
        "phase": "Long terme",
        "actions": [
            "Mettre en place des revues de code systématiques",
            "Automatiser les tests de sécurité",
            "Améliorer la couverture de tests"
        ],
        "owner": "Équipe entière",
        "timeline": "Continue"
    })
    
    return action_plan

def format_llm_report(enhanced_report):
    """Formate le rapport final pour l'affichage"""
    report_lines = []
    
    # 1. Overview
    report_lines.append("# Rapport d'Analyse de Sécurité et Qualité Amélioré\n")
    report_lines.append(enhanced_report["overview"])
    
    # 2. Security Analysis
    report_lines.append("\n## Analyse de Sécurité Détailée\n")
    for item in enhanced_report["security_analysis"]:
        report_lines.append(f"### {item['issue']} ({item['count']} occurrences, Severity: {item['severity']}")
        report_lines.append(f"**Description**: {item['description']}")
        report_lines.append("**Recommandations**:")
        for rec in item["recommendations"]:
            report_lines.append(f"- {rec}")
        report_lines.append("**Ressources**:")
        for res in item["resources"]:
            report_lines.append(f"- {res}")
        report_lines.append("")
    
    # 3. Code Quality Analysis
    report_lines.append("\n## Analyse de Qualité de Code\n")
    for item in enhanced_report["code_quality_analysis"]:
        report_lines.append(f"### {item['issue']} (Valeur: {item['value']}, Severity: {item['severity']}")
        report_lines.append(f"**Description**: {item['description']}")
        report_lines.append("**Recommandations**:")
        for rec in item["recommendations"]:
            report_lines.append(f"- {rec}")
        report_lines.append("**Ressources**:")
        for res in item["resources"]:
            report_lines.append(f"- {res}")
        report_lines.append("")
    
    # 4. Critical Issues
    if enhanced_report["critical_issues"]:
        report_lines.append("\n## Problèmes Critiques par Fichier\n")
        report_lines.append("| Fichier | Ligne | Type | Sévérité | Description |")
        report_lines.append("|---------|-------|------|----------|-------------|")
        for issue in enhanced_report["critical_issues"]:
            report_lines.append(f"| {issue['file']} | {issue['line']} | {issue['type']} | {issue['severity']} | {issue['description']} |")
    
    # 5. Detailed Recommendations
    report_lines.append("\n## Recommandations Détaillées\n")
    for rec in enhanced_report["detailed_recommendations"]:
        report_lines.append(f"### {rec['action']} (Priorité: {rec['priority']})")
        report_lines.append("**Étapes**:")
        for step in rec["steps"]:
            report_lines.append(f"- {step}")
        report_lines.append(f"**Temps estimé**: {rec['estimated_time']}")
        report_lines.append("")
    
    # 6. Action Plan
    report_lines.append("\n## Plan d'Action Priorisé\n")
    for phase in enhanced_report["action_plan"]:
        report_lines.append(f"### {phase['phase']} ({phase['timeline']})")
        report_lines.append(f"**Responsable**: {phase['owner']}")
        report_lines.append("**Actions**:")
        for action in phase["actions"]:
            report_lines.append(f"- {action}")
        report_lines.append("")
    
    return "\n".join(report_lines)

async def main():
    # Exemple d'utilisation
    # Configuration
    project_path = "C:/Users/hp/Desktop/Projets Django/Gestion-Travaux/gestion_travaux/travaux"
    gemini_api_key = "AIzaSyCNrCluPy7gFdDWXKJamd_RO5pZefATe5s" 
    
    # Initialisation
    analyzer = SecurityAnalyzer()
    llm_analyzer = LLMAnalyzer(gemini_api_key)
    
    # Analyse
    print("Analyse en cours...")
    analysis_results = analyzer.analyze_project(project_path)
    
    # Rapports
    print("\n=== RAPPORT DE BASE ===")
    print(analyzer.generate_report())
    
    print("\n=== RAPPORT AVANCÉ (IA) ===")
    try:
        llm_report = await generate_llm_report(analysis_results, llm_analyzer)
        #llm_report = generate_llm_report1(analysis_results)
        print(llm_report)
    except Exception as e:
        print(f"Échec de génération du rapport IA: {str(e)}")
    
    # Prédiction avec le modèle ML
    model = joblib.load('failles.pkl')
    
    # Création du DataFrame avec TOUTES les colonnes attendues par le modèle
    metrics = analyzer.report["summary_metrics"]
    
    # Liste COMPLÈTE des features attendues par le modèle
    expected_features = [
        "complexite_cyclomatique",
        "nombre_branches",
        "profondeur_heritage",
        "nombre_classes",
        "longueur_moyenne_fonctions",  # Ajouté
        "parametres_moyens_par_fonction",  # Ajouté
        "lignes_code_effectif",
        "lignes_commentaires",
        "code_duplique",
        "violations_pylint",
        "annotations_type",
        "variables_sensibles",
        "injections_sql",
        "xss_potentiels",
        "csrf_protection",
        "dependances_vulnerables",
        "api_key_exposure",
        "encryption_usage",
        "authorization_checks",
        "decorators_used",
        "http_endpoints"
    ]
    
    # 1. Créer un dictionnaire avec toutes les métriques disponibles
    filtered_metrics = {k: metrics[k] for k in metrics if k in expected_features}
    
    # 2. Ajouter les métriques manquantes avec une valeur par défaut (0)
    for feature in expected_features:
        if feature not in filtered_metrics:
            filtered_metrics[feature] = 0
    
    # 3. Créer le DataFrame dans le bon ordre
    df = pd.DataFrame([filtered_metrics])[expected_features]
    
    # Vérification finale
    print("\nVérification des colonnes:")
    print(df.columns.tolist())
    
    # Prédiction
    try:
        prediction = model.predict(df)
        
        print("\n*** Résultat de la Prédiction ***")
        if prediction[0] == 1:
            print("Défaut logiciel détecté (defaut_present = 1)")
        else:
            print("Aucun défaut logiciel détecté (defaut_present = 0)")
    except Exception as e:
        print(f"\nErreur lors de la prédiction: {str(e)}")
        print("Colonnes du DataFrame:", df.columns.tolist())
        print("Features attendues par le modèle:", model.feature_names_in_)

if __name__ == "__main__":
    asyncio.run(main())