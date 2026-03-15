#!/usr/bin/env python3
"""
AI code review script used by GitHub Actions PR Review workflow.
Optimized for Speed: Parallel processing & Category-based review.
"""
import json
import os
import subprocess
import traceback
import concurrent.futures

MAX_DIFF_LENGTH = 18000
# 限制最大并发数，避免 API 限流或 GitHub Action 资源耗尽
MAX_WORKERS = 3 

REVIEW_PATHS = [
    '*.py', '*.md', 'README.md', 'AGENTS.md', 'docs/**',
    '.github/PULL_REQUEST_TEMPLATE.md', 'requirements.txt',
    'pyproject.toml', 'setup.cfg', '.github/workflows/*.yml',
    '.github/scripts/*.py', 'apps/dsa-web/**',
]

def run_git(args):
    result = subprocess.run(args, capture_output=True, text=True)
    if result.returncode != 0:
        return ''
    return result.stdout.strip()

def get_changed_files():
    base_ref = os.environ.get('GITHUB_BASE_REF', 'main')
    output = run_git(['git', 'diff', '--name-only', f'origin/{base_ref}...HEAD', '--', *REVIEW_PATHS])
    return [f for f in output.split('\n') if f] if output else []

def get_pr_context():
    event_path = os.environ.get('GITHUB_EVENT_PATH')
    if not event_path or not os.path.exists(event_path):
        return '', ''
    try:
        with open(event_path, 'r', encoding='utf-8') as f:
            payload = json.load(f)
            pr = payload.get('pull_request', {})
            return (pr.get('title') or '').strip(), (pr.get('body') or '').strip()
    except Exception:
        return '', ''

def classify_files(files):
    py_files = [f for f in files if f.endswith('.py')]
    doc_files = [f for f in files if f.endswith('.md') or f.startswith('docs/') or f in ('README.md', 'AGENTS.md')]
    frontend_files = [f for f in files if f.startswith('apps/dsa-web/') or f.endswith(('.tsx', '.ts'))]
    others = [f for f in files if f not in py_files + doc_files + frontend_files]
    return py_files, doc_files, frontend_files, others

def build_prompt(diff_content, files, pr_title, pr_body, category_name):
    """构建针对特定类别的 Prompt"""
    return f"""你是仓库 PR 审查助手。正在进行【{category_name}】专项审查。

## PR 信息
- 标题: {pr_title or '(empty)'}
- 描述: {pr_body or '(empty)'}

## 待审文件列表
{', '.join(files)}

## 代码变更 (diff)
```diff
{diff_content[:MAX_DIFF_LENGTH]}
