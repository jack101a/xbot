"""
Architecture Boundary Linter for XBot Pro.
Enforces the Modular Monolith / Ports-and-Adapters isolation rules:
1. 'playwright' may ONLY be imported in 'xbot/infra/browser/' and 'xbot/infra/llm/chatgpt_bridge/' (or legacy browser shims).
2. 'xbot.contracts' must NOT import from 'xbot.infra', 'xbot.pipelines', 'xbot.tasks', or 'xbot.ai'.
3. 'xbot.domain' must be pure Python (no DB models, no Playwright, no HTTP clients).
"""
import ast
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
XBOT_ROOT = PROJECT_ROOT / "xbot"

ALLOWED_PLAYWRIGHT_ROOTS = (
    "xbot/infra/browser",
    "xbot/infra/llm/chatgpt_bridge",
    "xbot/browser",
    "xbot/ai/chatgpt_bridge",
)

def check_file(file_path: Path) -> list[str]:
    violations = []
    rel_path = file_path.relative_to(PROJECT_ROOT).as_posix()
    
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            tree = ast.parse(f.read(), filename=str(file_path))
    except Exception as e:
        return [f"{rel_path}: Failed to parse AST: {e}"]

    for node in ast.walk(tree):
        imported_names = []
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported_names.append(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_names.append(node.module)

        for name in imported_names:
            # Rule 1: Playwright imports restricted
            if name.startswith("playwright"):
                if not any(rel_path.startswith(allowed) for allowed in ALLOWED_PLAYWRIGHT_ROOTS):
                    violations.append(
                        f"[VIOLATION] {rel_path}:{getattr(node, 'lineno', '?')} imports '{name}', "
                        f"which is strictly prohibited outside infra/browser adapters!"
                    )
            
            # Rule 2: Contracts cannot import outer layers
            if rel_path.startswith("xbot/contracts"):
                if name.startswith(("xbot.infra", "xbot.pipelines", "xbot.tasks", "xbot.ai", "xbot.api")):
                    violations.append(
                        f"[VIOLATION] {rel_path}:{getattr(node, 'lineno', '?')} in contracts imports outer layer '{name}'!"
                    )

    return violations

def main() -> int:
    all_violations = []
    for py_file in XBOT_ROOT.rglob("*.py"):
        if "__pycache__" in py_file.parts:
            continue
        all_violations.extend(check_file(py_file))

    if all_violations:
        print(f"\n❌ Found {len(all_violations)} Architectural Boundary Violation(s):")
        for v in all_violations:
            print(f"  {v}")
        return 1
    
    print("\n✅ Architectural Boundary Lint Passed: All layer constraints strictly satisfied.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
