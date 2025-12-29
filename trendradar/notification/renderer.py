# coding=utf-8
"""
通知内容渲染模块

提供多平台通知内容渲染功能，生成格式化的推送消息
"""

from datetime import datetime
from typing import Dict, Optional, Callable

from trendradar.report.formatter import format_title_for_platform


def render_feishu_content(
    report_data: Dict,
    update_info: Optional[Dict] = None,
    mode: str = "daily",
    separator: str = "---",
    reverse_content_order: bool = False,
    get_time_func: Optional[Callable[[], datetime]] = None,
) -> str:
    # 辅助工具：提取链接或格式化
    def format_item_visual(title_data: Dict, show_source: bool = True) -> str:
        """
        深度优化：物理分离标题、元数据和链接
        """
        title = title_data.get("title", "无标题").strip()
        url = title_data.get("url", "")
        source = f"  |  来源：{title_data.get('source_name')}" if show_source else ""
        hot_val = f"  |  热度：{title_data.get('hot_value', 'N/A')}" if title_data.get('hot_value') else ""

        # 第一行：标题加粗
        # 第二行：辅助信息（来源、热度）- 灰色小字
        # 第三行：链接独立（飞书会自动识别链接或点击跳转）
        item_str = f"**{title}**\n"
        item_str += f"<font color='grey'>📍 {source}{hot_val}</font>\n"
        if url:
            item_str += f"🔗 [查看详情]({url})\n"
        return item_str

    # 1. 渲染热点词汇统计 (Stats Section)
    stats_sections = []
    if report_data["stats"]:
        for i, stat in enumerate(report_data["stats"]):
            word = stat["word"]
            count = stat["count"]
            
            # 根据权重选择Icon
            icon = "🔥" if count >= 10 else ("📈" if count >= 5 else "📌")
            header = f"{icon} **关键词：{word}** ({count}条相关)\n"
            
            items = []
            for j, title_data in enumerate(stat["titles"], 1):
                # 调用可视化格式化函数
                formatted = format_item_visual(title_data, show_source=True)
                items.append(f"{j}. {formatted}")
            
            stats_sections.append(header + "\n".join(items))

    # 2. 渲染新增热点 (New Titles Section)
    new_titles_sections = []
    if report_data["new_titles"]:
        header_main = f"🆕 **本次新增热点** (共计 {report_data['total_new_count']} 条)\n"
        
        detail_blocks = []
        for source_data in report_data["new_titles"]:
            source_header = f"🔹 **{source_data['source_name']}**"
            source_items = []
            for j, title_data in enumerate(source_data["titles"], 1):
                formatted = format_item_visual(title_data, show_source=False)
                source_items.append(f"  {j}. {formatted}")
            detail_blocks.append(f"{source_header}\n" + "\n".join(source_items))
        
        new_titles_sections.append(header_main + "\n".join(detail_blocks))

    # 3. 组装内容
    segments = []
    if reverse_content_order:
        segments.extend(new_titles_sections)
        segments.extend(stats_sections)
    else:
        segments.extend(stats_sections)
        segments.extend(new_titles_sections)

    # 4. 空态处理
    if not any(segments):
        mode_map = {
            "incremental": "增量模式下暂无匹配热点词汇",
            "current": "当前榜单暂无匹配热点词汇"
        }
        text_content = f"📭 {mode_map.get(mode, '暂无匹配的热点词汇')}\n"
    else:
        text_content = f"\n\n{separator}\n\n".join(segments)

    # 5. 失败平台提示
    if report_data["failed_ids"]:
        fail_str = f"\n\n⚠️ **异常监控**\n<font color='red'>以下平台获取数据失败：</font>\n"
        fail_str += " · " + "  · ".join(report_data["failed_ids"])
        text_content += fail_str

    # 6. 页脚与版本信息
    now = get_time_func() if get_time_func else datetime.now()
    footer = f"\n\n{separator}\n"
    footer += f"<font color='grey'>📅 更新：{now.strftime('%Y-%m-%d %H:%M:%S')}</font>"
    
    if update_info:
        footer += f"\n<font color='grey'>🚀 新版本提醒：{update_info['current_version']} -> {update_info['remote_version']}</font>"
    
    return text_content + footer


def render_dingtalk_content(
    report_data: Dict,
    update_info: Optional[Dict] = None,
    mode: str = "daily",
    reverse_content_order: bool = False,
    get_time_func: Optional[Callable[[], datetime]] = None,
) -> str:
    """渲染钉钉通知内容

    Args:
        report_data: 报告数据字典，包含 stats, new_titles, failed_ids, total_new_count
        update_info: 版本更新信息（可选）
        mode: 报告模式 ("daily", "incremental", "current")
        reverse_content_order: 是否反转内容顺序（新增在前）
        get_time_func: 获取当前时间的函数（可选，默认使用 datetime.now()）

    Returns:
        格式化的钉钉消息内容
    """
    total_titles = sum(
        len(stat["titles"]) for stat in report_data["stats"] if stat["count"] > 0
    )
    now = get_time_func() if get_time_func else datetime.now()

    # 头部信息
    header_content = f"**总新闻数：** {total_titles}\n\n"
    header_content += f"**时间：** {now.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
    header_content += "**类型：** 热点分析报告\n\n"
    header_content += "---\n\n"

    # 生成热点词汇统计部分
    stats_content = ""
    if report_data["stats"]:
        stats_content += "📊 **热点词汇统计**\n\n"

        total_count = len(report_data["stats"])

        for i, stat in enumerate(report_data["stats"]):
            word = stat["word"]
            count = stat["count"]

            sequence_display = f"[{i + 1}/{total_count}]"

            if count >= 10:
                stats_content += f"🔥 {sequence_display} **{word}** : **{count}** 条\n\n"
            elif count >= 5:
                stats_content += f"📈 {sequence_display} **{word}** : **{count}** 条\n\n"
            else:
                stats_content += f"📌 {sequence_display} **{word}** : {count} 条\n\n"

            for j, title_data in enumerate(stat["titles"], 1):
                formatted_title = format_title_for_platform(
                    "dingtalk", title_data, show_source=True
                )
                stats_content += f"  {j}. {formatted_title}\n"

                if j < len(stat["titles"]):
                    stats_content += "\n"

            if i < len(report_data["stats"]) - 1:
                stats_content += "\n---\n\n"

    # 生成新增新闻部分
    new_titles_content = ""
    if report_data["new_titles"]:
        new_titles_content += (
            f"🆕 **本次新增热点新闻** (共 {report_data['total_new_count']} 条)\n\n"
        )

        for source_data in report_data["new_titles"]:
            new_titles_content += f"**{source_data['source_name']}** ({len(source_data['titles'])} 条):\n\n"

            for j, title_data in enumerate(source_data["titles"], 1):
                title_data_copy = title_data.copy()
                title_data_copy["is_new"] = False
                formatted_title = format_title_for_platform(
                    "dingtalk", title_data_copy, show_source=False
                )
                new_titles_content += f"  {j}. {formatted_title}\n"

            new_titles_content += "\n"

    # 根据配置决定内容顺序
    text_content = header_content
    if reverse_content_order:
        # 新增热点在前，热点词汇统计在后
        if new_titles_content:
            text_content += new_titles_content
            if stats_content:
                text_content += "\n---\n\n"
        if stats_content:
            text_content += stats_content
    else:
        # 默认：热点词汇统计在前，新增热点在后
        if stats_content:
            text_content += stats_content
            if new_titles_content:
                text_content += "\n---\n\n"
        if new_titles_content:
            text_content += new_titles_content

    if not stats_content and not new_titles_content:
        if mode == "incremental":
            mode_text = "增量模式下暂无新增匹配的热点词汇"
        elif mode == "current":
            mode_text = "当前榜单模式下暂无匹配的热点词汇"
        else:
            mode_text = "暂无匹配的热点词汇"
        text_content += f"📭 {mode_text}\n\n"

    if report_data["failed_ids"]:
        if "暂无匹配" not in text_content:
            text_content += "\n---\n\n"

        text_content += "⚠️ **数据获取失败的平台：**\n\n"
        for i, id_value in enumerate(report_data["failed_ids"], 1):
            text_content += f"  • **{id_value}**\n"

    text_content += f"\n\n> 更新时间：{now.strftime('%Y-%m-%d %H:%M:%S')}"

    if update_info:
        text_content += f"\n> TrendRadar 发现新版本 **{update_info['remote_version']}**，当前 **{update_info['current_version']}**"

    return text_content
