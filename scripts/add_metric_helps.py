#!/usr/bin/env python3
"""Add metricHelp to remaining charts in team_player_usage.html"""

# Metric help definitions in Russian
metric_helps = {
    '💥 Star WR Dependency vs Interception Risk': '<strong>INT Rate:</strong> Процент перехватов от общего числа передач. Показывает, приводит ли зависимость от одного WR к предсказуемым передачам и перехватам.',
    '💥 Bellcow Power: Workload vs Physicality': '<strong>Broken Tackles Rate:</strong> Процент разорванных захватов на вынос. Показывает физическую мощь RB - элитные бегуны vs свежие ноги комитета.',
    '💥 Predictability Tax: Target Concentration vs Sacks': '<strong>Sack Rate:</strong> Процент сэков от (попытки + сэки). Концентрация на одном приёмнике = предсказуемость = больше сэков?',
    '💥 TE Usage: Weapon or Safety Blanket?': '<strong>TE + Sacks:</strong> Высокое использование TE с низкими сэками = оружие защиты. Высокие оба = последнее средство под давлением.',
    '💥 Star Power vs Offensive Efficiency': '<strong>Yards per Play:</strong> Средние ярды за розыгрыш. Элитные приёмники разблокируют эффективность или распределение мяча держит защиту в напряжении?',
    '💥 Bellcow Effectiveness Test': '<strong>Rush Y/A:</strong> Ярды за вынос. Проверка эффективности: один бегун vs свежие ноги комитета - кто производит больше ярдов?',
    '💥 Star WR Impact on QB Performance': '<strong>QB Rating:</strong> Рейтинг квотербека. Элитный WR1 повышает игру QB или элитный QB делает WR1 звездой? Курица или яйцо?',
    '💥 RB Checkdown Strategy: Smart or Desperate?': '<strong>Pass Y/A:</strong> Ярды за попытку паса. Высокие передачи RB + высокий Y/A = оружие. Высокие RB + низкий Y/A = сброс под давлением.',
    '💥 Distribution Strategy vs Big Plays': '<strong>Explosive Plays:</strong> Розыгрыши 20+ ярдов за игру. Распределение мяча создаёт больше взрывных моментов или звёзды делают большие игры?',
    '💥 Ball Security: Bellcow vs Committee': '<strong>Turnovers:</strong> Общие потери мяча. Основные бегуны теряют больше от усталости или у комитетов хуже контроль мяча?',
    '💥 WR-Heavy Offense Scoring Efficiency': '<strong>Pass TD Rate:</strong> Процент тачдаунов от попыток передач. WR-центричные атаки забивают больше TD или TE/RB лучше в красной зоне?',
    '💥 TE Usage: High-Percentage Safety Valve': '<strong>Completion %:</strong> Процент завершённых передач. TE = более лёгкие броски = выше процент? Доказательство, что TE - ultimate подстраховка.',
    '💥 Star Receivers & Ball Protection': '<strong>Turnover Diff:</strong> Разница потерь мяча (отборы - отдачи). Элитные приёмники лучше защищают мяч или команды с топ-WR просто лучше в целом?',
    '💥 Goal Line Back: Who Gets the Glory?': '<strong>Rush TD Rate:</strong> Процент тачдаунов от выносов. Bellcow доминируют на линии ворот или комитеты ротируют силовых бегунов для TD?',
    '💥 Target Overload: Does WR1 Drop More?': '<strong>Drop Rate:</strong> Процент потерянных передач от целей. Кормление одного приёмника = больше потерь от усталости или у элитных WR лучше руки?',
    '💥 RB Receptions: YAC Machines or Dump-offs?': '<strong>YAC %:</strong> Процент ярдов после приёма. Высокие передачи RB + высокий YAC% = динамичное оружие. Высокий RB + низкий YAC% = сброс на линии.'
}

import re

# Read the file
with open('/Users/lespaul/Downloads/MEGA_neonsportz_stats/docs/team_player_usage.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Add metricHelp to charts that don't have it yet
for title, help_text in metric_helps.items():
    # Escape special regex characters in title
    escaped_title = re.escape(title)
    
    # Pattern to find chart config for this title
    pattern = rf"(title: '{escaped_title}',\s+insight: '[^']+')(,?\s*extraInfo:)"
    
    # Check if metricHelp already exists for this title
    if not re.search(rf"title: '{escaped_title}'[^}}]+metricHelp:", content):
        # Add metricHelp before extraInfo if it exists
        replacement = rf"\1,\n            metricHelp: '{help_text}'\2"
        content = re.sub(pattern, replacement, content)
        
    # Pattern for charts without extraInfo
    pattern2 = rf"(title: '{escaped_title}',\s+insight: '[^']+'\s*)(}})"
    if not re.search(rf"title: '{escaped_title}'[^}}]+metricHelp:", content):
        replacement2 = rf"\1,\n            metricHelp: '{help_text}'\n          \2"
        content = re.sub(pattern2, replacement2, content)

# Write back
with open('/Users/lespaul/Downloads/MEGA_neonsportz_stats/docs/team_player_usage.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("✓ Added metricHelp to all remaining charts")
