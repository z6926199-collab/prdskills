#!/usr/bin/env python3
"""Validate Markdown PRDs against the TCL product-planning template."""

from __future__ import annotations

import re
import sys
from pathlib import Path


REQUIRED_HEADINGS = [
    "# 一、需求概述 (必备)",
    "## 1.1 概述(必备)",
    "## 1.2 变更日志(必备)",
    "## 1.3 评审记录(必备)",
    "# 二、 需求背景(必备)",
    "## 2.1 背景说明(必备)",
    "## 2.2 产品 / 数据现状(产品迭代必备)",
    "## 2.3 用户调研",
    "## 2.4 竞品分析(必备)",
    "# 三、需求目标(必备)",
    "# 四、 需求列表(必备)",
    "# 五、 功能详细说明(必备)",
    "## 5.1 产品流程图",
    "## 5.2 交互原型图",
    "## 5.3 功能说明(必备)",
    "# 六、 非功能需求(必备)",
    "### 6.1 数据统计需求",
    "### 6.2 升级产品需求",
    "### 6.3 语音需求",
    "### 6.4 需求依赖",
    "#### 6.4.1 硬件依赖",
    "#### 6.4.2 软件依赖",
    "### 6.5 隐私合规及权限控制需求",
    "### 6.6 国际化需求（含翻译）",
    "### 6.7 其他Checklist",
    "### 6.8 词条提报",
    "### 6.9 FAQ/使用技巧/帮助与反馈",
    "### 6.10 演示体系/卖场模式",
    "## 七、附件",
    "# 附录",
]

FEATURE_FIELDS = [
    "功能",
    "功能详细说明",
    "功能入口/前置条件",
    "具体表现",
    "相关定义说明",
    "边界场景",
    "逆向场景/退化逻辑（与前置条件相反时）",
    "异常场景",
    "极限场景",
]

FORBIDDEN_HEADING_PATTERNS = [
    r"^#{1,6}\s+5\.2\.1\b",
    r"^#{1,6}\s+6\.11\b",
    r"^#{1,6}\s+.*证据追溯表",
    r"^#{1,6}\s+.*评审更新记录",
]

REQUIRED_CHECKLIST_TERMS = ["玩机技巧", "NXTPAPER", "应用分身", "去TCL化"]

REQUIRED_TABLE_HEADERS = [
    "| 需求名称 | 一句话描述需要实现的需求 |",
    "| 时间 | 版本号 | 变更人 | 主要变更内容 |",
    "| 评审记录 | 评审结论 | 评审人 | 时间 | 备注 |",
    "| | 主要信息 | 关键结论 | 截图或视频 |",
    "| 指标名称 | 目标 | 验收方式 |",
    "| 指标名称 | 监控原因/说明 | 涉及埋点名称可直接附埋点文档 | 埋点上报时机 |",
    "| 依赖项 | 依赖说明 | 备注 |",
    "| 依赖分类 | 依赖项 | 依赖说明 | 提供方/开发组织 | 风险 |",
    "| 个人/隐私数据 | 数据的用途 |",
    "| 需要豁免权限 | 权限的用途 |",
    "| 业务线 | 涉及方 | 涉及问题 |",
    "| 附件名称 | 附件链接 | 备注 |",
]

OVERVIEW_FIELDS = ["需求名称", "预期上线时间", "上线机型", "需求提出方", "编写人", "创建时间"]


def table_cells(line: str) -> list[str]:
    return [cell.strip().replace("**", "") for cell in line.strip().strip("|").split("|")]


def validate(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    errors: list[str] = []

    if not re.search(r"^# .+需求文档【产品规划部模板】$", text, re.MULTILINE):
        errors.append("文档标题必须为“# [需求名称]需求文档【产品规划部模板】”")

    cursor = -1
    for heading in REQUIRED_HEADINGS:
        try:
            cursor = lines.index(heading, cursor + 1)
        except ValueError:
            errors.append(f"缺少或顺序错误：{heading}")

    for line_no, line in enumerate(lines, 1):
        for pattern in FORBIDDEN_HEADING_PATTERNS:
            if re.match(pattern, line):
                errors.append(f"第 {line_no} 行出现模板外章节：{line}")

    for header in REQUIRED_TABLE_HEADERS:
        if header not in lines:
            errors.append(f"缺少或改动了固定表头：{header}")

    try:
        overview_start = lines.index("## 1.1 概述(必备)")
        overview_end = lines.index("## 1.2 变更日志(必备)", overview_start + 1)
        overview_lines = [
            line for line in lines[overview_start + 1 : overview_end] if line.strip().startswith("|")
        ]
        overview_actual = [table_cells(line)[0] for line in overview_lines if not re.match(r"^\|[-|]+\|?$", line)]
        if overview_actual != OVERVIEW_FIELDS:
            errors.append("1.1 概述字段必须仅为：需求名称、预期上线时间、上线机型、需求提出方、编写人、创建时间")
    except ValueError:
        pass

    feature_heading_indexes = [
        index for index, line in enumerate(lines) if re.match(r"^### 5\.3\.\d+\s+", line)
    ]
    if not feature_heading_indexes:
        errors.append("5.3 下至少需要一个形如“### 5.3.1 功能名”的功能节")

    for index in feature_heading_indexes:
        end = next(
            (
                next_index
                for next_index in range(index + 1, len(lines))
                if re.match(r"^#{1,3}\s+", lines[next_index])
            ),
            len(lines),
        )
        block = lines[index + 1 : end]
        header_index = next((i for i, line in enumerate(block) if line.strip().startswith("|")), None)
        label = lines[index]
        if header_index is None:
            errors.append(f"{label} 缺少 5.3 表格")
            continue

        table_lines = []
        for line in block[header_index:]:
            if not line.strip().startswith("|"):
                break
            table_lines.append(line)

        if len(table_lines) < 11:
            errors.append(f"{label} 表格行数不足，应为表头、分隔行和 9 个字段行")
            continue

        if table_cells(table_lines[0]) != ["字段", "功能描述", "原型图"]:
            errors.append(f"{label} 表头必须为：字段 | 功能描述 | 原型图")

        actual_fields = [table_cells(line)[0] for line in table_lines[2:] if table_cells(line)]
        if actual_fields != FEATURE_FIELDS:
            errors.append(f"{label} 的 9 个字段名或顺序不符合模板")

        for offset, line in enumerate(table_lines):
            if len(table_cells(line)) != 3:
                errors.append(f"{label} 的表格第 {offset + 1} 行不是三列")

    for term in REQUIRED_CHECKLIST_TERMS:
        if term not in text:
            errors.append(f"6.7 Checklist 缺少：{term}")

    return errors


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: validate_prd_template.py <prd.md>")
        return 2

    path = Path(sys.argv[1])
    if not path.is_file():
        print(f"File not found: {path}")
        return 2

    errors = validate(path)
    if errors:
        print("模板校验失败：")
        for error in errors:
            print(f"- {error}")
        return 1

    print("模板校验通过")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
