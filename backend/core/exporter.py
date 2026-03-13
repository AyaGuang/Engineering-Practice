"""导出模块 - 支持CSV和HTML报告"""
import csv
import os
from models.result import GradingReport


def export_csv(report: GradingReport, file_path: str):
    """导出批改结果为CSV文件"""
    with open(file_path, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        writer.writerow(['题号', '题型', '识别文字', '标准答案', '是否正确', '匹配度', '得分', '满分'])
        for r in report.results:
            writer.writerow([
                r.question.number,
                r.question.q_type.display_name,
                r.recognized_text,
                r.question.standard_answer,
                '正确' if r.is_correct else '错误',
                f'{r.match_score:.0%}',
                r.earned_points,
                r.question.points,
            ])
        writer.writerow([])
        writer.writerow(['总分', '', '', '', '', '', report.earned_points, report.total_points])
        writer.writerow(['得分率', '', '', '', '', '', f'{report.percentage:.1f}%', ''])


def export_html(report: GradingReport, file_path: str):
    """导出批改结果为HTML报告"""
    rows = ''
    for r in report.results:
        color = '#d4edda' if r.is_correct else '#f8d7da'
        rows += f'''        <tr style="background-color: {color};">
            <td>{r.question.number}</td>
            <td>{r.question.q_type.display_name}</td>
            <td>{r.recognized_text}</td>
            <td>{r.question.standard_answer}</td>
            <td>{'✓ 正确' if r.is_correct else '✗ 错误'}</td>
            <td>{r.match_score:.0%}</td>
            <td>{r.earned_points}</td>
            <td>{r.question.points}</td>
        </tr>
'''

    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>批改报告</title>
    <style>
        body {{ font-family: "Microsoft YaHei", sans-serif; margin: 40px; }}
        h1 {{ color: #333; }}
        table {{ border-collapse: collapse; width: 100%; margin-top: 20px; }}
        th, td {{ border: 1px solid #ddd; padding: 10px; text-align: center; }}
        th {{ background-color: #4a90d9; color: white; }}
        .summary {{ margin-top: 20px; font-size: 18px; font-weight: bold; }}
    </style>
</head>
<body>
    <h1>手写作业批改报告</h1>
    <table>
        <thead>
            <tr>
                <th>题号</th><th>题型</th><th>识别文字</th><th>标准答案</th>
                <th>结果</th><th>匹配度</th><th>得分</th><th>满分</th>
            </tr>
        </thead>
        <tbody>
{rows}        </tbody>
    </table>
    <div class="summary">
        总分: {report.earned_points} / {report.total_points} ({report.percentage:.1f}%)
    </div>
</body>
</html>'''

    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(html)
