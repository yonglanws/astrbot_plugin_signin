import os
import base64
import random
import secrets
import shutil
import sqlite3
import threading
import io
from PIL import Image
from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
from astrbot.api import AstrBotConfig
import astrbot.api.message_components as Comp
import jinja2
import json
from datetime import datetime, timedelta
from pathlib import Path

DIFFICULTY_ORDER = {'hard': 0, 'expert': 1, 'master': 2, 'append': 2}
DIFFICULTY_LABEL_MAP = {'hard': 'HARD', 'expert': 'EXPERT', 'master': 'MASTER', 'append': 'APPEND'}

def _secure_random_choice(items):
    """使用加密级随机数生成器进行公平选择"""
    if not items:
        return None
    secure_index = secrets.randbelow(len(items))
    return items[secure_index]

def select_song_with_difficulty(songs, first_difficulty_type=None, first_difficulty_level=None):
    """
    根据难度相似性选择歌曲，使用加密级随机数保证公平性
    相似性标准:
      - 同难度类型: ±5
      - 相邻难度类型: ±7
      - 非相邻难度类型: 不视为相似
    """
    if not songs:
        return []

    first_song = _secure_random_choice(songs)
    if first_song is None:
        return []

    first_diff_info = _extract_best_difficulty(first_song)
    if first_diff_info:
        first_difficulty_type = first_diff_info['type']
        first_difficulty_level = first_diff_info['level']

    similar_songs = _find_similar_songs(songs, first_difficulty_type, first_difficulty_level, exclude_ids=[first_song.get('id')])

    if similar_songs:
        second_song = _secure_random_choice(similar_songs)
    else:
        logger.warning(f"⚠️ 未找到与难度 {first_difficulty_type}{first_difficulty_level} 相似的歌曲，随机选择")
        candidates = [s for s in songs if s.get('id') != first_song.get('id')]
        if candidates:
            second_song = _secure_random_choice(candidates)
        else:
            second_song = first_song

    result = []
    for song in [first_song, second_song]:
        diff_info = _extract_best_difficulty(song)
        song_copy = song.copy()
        if diff_info:
            song_copy['difficulty_type'] = diff_info['type']
            song_copy['difficulty_level'] = diff_info['level']
            song_copy['difficulty_label'] = DIFFICULTY_LABEL_MAP.get(diff_info['type'], diff_info['type'].capitalize())
        else:
            song_copy['difficulty_type'] = None
            song_copy['difficulty_level'] = None
            song_copy['difficulty_label'] = None
        result.append(song_copy)

    return result

def _extract_best_difficulty(song):
    """从歌曲中提取一个难度信息（随机选择，保证各种难度都有机会显示）"""
    difficulties = song.get('difficulties', [])
    if not difficulties:
        return None

    diff = _secure_random_choice(difficulties)
    if diff:
        return {
            'type': diff.get('musicDifficulty', ''),
            'level': diff.get('playLevel', 0)
        }
    return None

def _find_similar_songs(songs, difficulty_type, difficulty_level, exclude_ids=None):
    """查找与指定难度相似的歌曲（仅比较数字难度值）"""
    if exclude_ids is None:
        exclude_ids = []

    if difficulty_level is None:
        return [s for s in songs if s.get('id') not in exclude_ids]

    similar = []
    level_threshold = 7

    for song in songs:
        song_id = song.get('id')
        if song_id in exclude_ids:
            continue

        difficulties = song.get('difficulties', [])
        if not difficulties:
            continue

        for diff in difficulties:
            diff_level = diff.get('playLevel', 0)
            level_diff = abs(diff_level - difficulty_level)

            if level_diff <= level_threshold:
                similar.append(song)
                break

    return similar

TMPL = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=2400, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>签到成功</title>
    <style>
        @font-face {
            font-family: 'MiSans';
            src: url(data:font/ttf;base64,{{base64_font}}) format('truetype');
            font-weight: 500;
            font-style: normal;
        }

        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
            font-family: 'MiSans', -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', sans-serif;
        }

        body {
            height: 2160px;
            width: 2400px;
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 60px;
            position: relative;
            overflow: hidden;
        }

        .bg-layer {
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background-image: url('{{b64bg}}');
            background-repeat: no-repeat;
            background-position: center center;
            background-size: cover;
            z-index: 0;
        }

        .main-wrapper {
            display: flex;
            gap: 40px;
            width: 100%;
            max-width: 2280px;
            height: calc(2160px - 120px);
            align-items: stretch;
            position: relative;
            z-index: 1;
        }

        .divider {
            width: 4px;
            background: linear-gradient(180deg, 
                rgba(255,255,255,0) 0%, 
                rgba(255,255,255,0.7) 15%, 
                rgba(255,255,255,0.7) 85%, 
                rgba(255,255,255,0) 100%);
            border-radius: 2px;
            box-shadow: 0 0 30px rgba(255,255,255,0.4);
            flex-shrink: 0;
        }

        .left-panel {
            flex: 0 0 880px;
            background: rgba(255, 255, 255, 0.25);
            backdrop-filter: blur(28px);
            -webkit-backdrop-filter: blur(28px);
            border-radius: 52px;
            padding: 52px 42px;
            box-shadow: 0 8px 24px rgba(0, 0, 0, 0.08), inset 0 1px 0 rgba(255, 255, 255, 0.4);
            text-align: center;
            border: 1px solid rgba(255, 255, 255, 0.35);
            position: relative;
            overflow: hidden;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            align-self: center;
        }

        .right-panel {
            flex: 1;
            display: flex;
            flex-direction: column;
            min-width: 0;
        }

        .success-icon {
            width: 320px;
            height: 320px;
            margin: 0 auto 26px;
            display: flex;
            align-items: center;
            justify-content: center;
            overflow: visible;
            position: relative;
        }

        .success-icon img {
            width: 100%;
            height: 100%;
            object-fit: contain;
            filter: drop-shadow(0 10px 20px rgba(0,0,0,0.4));
            transform: scale(1.18);
        }

        h1 {
            font-size: 68px;
            font-weight: 800;
            color: white;
            margin-bottom: 22px;
            text-shadow: 0 4px 16px rgba(0, 0, 0, 0.35), 0 2px 4px rgba(0, 0, 0, 0.25);
            letter-spacing: 2px;
            line-height: 1.18;
        }

        .date-time {
            font-size: 44px;
            color: rgba(255, 255, 255, 0.95);
            margin-bottom: 38px;
            padding-bottom: 32px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.25);
            font-weight: 500;
            text-shadow: 0 2px 12px rgba(0, 0, 0, 0.3), 0 1px 3px rgba(0, 0, 0, 0.2);
            line-height: 1.4;
        }

        .fortune-box {
            background: rgba(255, 255, 255, 0.20);
            backdrop-filter: blur(18px);
            border-radius: 32px;
            padding: 0;
            margin-bottom: 34px;
            border: 1px solid rgba(255, 255, 255, 0.28);
            display: flex;
            align-items: stretch;
            box-shadow:
                0 10px 28px rgba(0, 0, 0, 0.22),
                inset 0 1px 0 rgba(255, 255, 255, 0.3);
            overflow: hidden;
            transition: all 0.3s ease;
            min-height: 112px;
        }

        .fortune-level {
            flex: 0 0 210px;
            font-size: 68px;
            font-weight: 800;
            color: white;
            text-shadow: 0 4px 16px rgba(0, 0, 0, 0.35), 0 2px 4px rgba(0, 0, 0, 0.25);
            line-height: 1.2;
            padding: 26px 20px;
            text-align: center;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: background 0.3s ease;
            min-height: 120px;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }

        .fortune-description {
            flex: 1;
            font-size: 46px;
            color: white;
            text-shadow: 0 2px 12px rgba(0, 0, 0, 0.3), 0 1px 3px rgba(0, 0, 0, 0.2);
            line-height: 1.38;
            font-weight: 600;
            padding: 26px 24px;
            text-align: right;
            display: flex;
            align-items: center;
            justify-content: flex-end;
            transition: background 0.3s ease;
            min-height: 120px;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            margin-left: 10px;
        }

        .fortune-box.good .fortune-level,
        .fortune-box.good .fortune-description {
            background: rgba(74, 222, 128, 0.25);
        }
        .fortune-box.good {
            border-color: rgba(74, 222, 128, 0.5);
        }

        .fortune-box.bad .fortune-level,
        .fortune-box.bad .fortune-description {
            background: rgba(239, 68, 68, 0.28);
        }
        .fortune-box.bad {
            border-color: rgba(239, 68, 68, 0.55);
        }

        .fortune-box.neutral .fortune-level,
        .fortune-box.neutral .fortune-description {
            background: rgba(255, 193, 7, 0.25);
        }
        .fortune-box.neutral {
            border-color: rgba(255, 193, 7, 0.5);
        }

        .fortune {
            display: flex;
            justify-content: space-around;
            gap: 22px;
            margin-bottom: 36px;
            position: relative;
        }

        .fortune-item {
            flex: 1;
            padding: 44px 24px;
            border-radius: 32px;
            backdrop-filter: blur(22px);
            border: 1px solid rgba(255, 255, 255, 0.35);
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 18px;
            overflow: visible;
            position: relative;
            box-shadow:
                0 8px 24px rgba(0, 0, 0, 0.18),
                inset 0 1px 0 rgba(255, 255, 255, 0.25);
        }

        .fortune-item.good {
            background: rgba(74, 222, 128, 0.35);
            border-color: rgba(74, 222, 128, 0.55);
        }

        .fortune-item.bad {
            background: rgba(239, 68, 68, 0.35);
            border-color: rgba(239, 68, 68, 0.55);
        }

        .fortune-icon {
            width: 180px;
            height: 180px;
            display: flex;
            align-items: center;
            justify-content: center;
            overflow: visible;
            position: relative;
        }

        .fortune-icon img {
            width: 100%;
            height: 100%;
            object-fit: contain;
            filter: drop-shadow(0 6px 14px rgba(0,0,0,0.35));
            transform: scale(1.28);
        }

        .fortune-label {
            font-size: 40px;
            color: rgba(255, 255, 255, 0.95);
            font-weight: 800;
            text-transform: uppercase;
            letter-spacing: 4px;
            text-shadow: 0 2px 12px rgba(0, 0, 0, 0.3), 0 1px 3px rgba(0, 0, 0, 0.2);
        }

        .fortune-value {
            font-size: 50px;
            color: white;
            font-weight: 800;
            text-shadow: 0 4px 16px rgba(0, 0, 0, 0.35), 0 2px 4px rgba(0, 0, 0, 0.25);
            line-height: 1.32;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }

        /* 左侧歌曲推荐样式 */
        .song-section {
            margin-top: 24px;
            padding: 22px;
            background: rgba(255, 255, 255, 0.18);
            backdrop-filter: blur(16px);
            border-radius: 28px;
            border: 1px solid rgba(255, 255, 255, 0.3);
            box-shadow:
                0 8px 24px rgba(0, 0, 0, 0.18),
                inset 0 1px 0 rgba(255, 255, 255, 0.25);
        }

        .song-section-title {
            font-size: 34px;
            font-weight: 700;
            color: white;
            text-shadow: 0 2px 12px rgba(0, 0, 0, 0.3), 0 1px 3px rgba(0, 0, 0, 0.2);
            margin-bottom: 16px;
            letter-spacing: 2px;
            text-align: left;
        }

        .song-info-left {
            display: flex;
            align-items: center;
            gap: 20px;
            background: rgba(255, 255, 255, 0.15);
            border-radius: 20px;
            padding: 16px 20px;
            border: 1px solid rgba(255, 255, 255, 0.25);
            position: relative;
        }

        .song-info-second {
            margin-top: 14px;
        }

        .song-cover-left {
            width: 120px;
            height: 120px;
            border-radius: 20px;
            object-fit: cover;
            box-shadow: 0 8px 24px rgba(0, 0, 0, 0.42);
            flex-shrink: 0;
        }

        .song-details-left {
            flex: 1;
            display: flex;
            flex-direction: column;
            gap: 6px;
            text-align: left;
            padding-right: 115px;
        }

        .song-difficulty-badge {
            position: absolute;
            right: 18px;
            top: 50%;
            transform: translateY(-50%);
            width: 100px;
            height: 100px;
            border-radius: 18px;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            gap: 6px;
            box-shadow: 0 6px 18px rgba(0, 0, 0, 0.35);
            backdrop-filter: blur(4px);
            -webkit-backdrop-filter: blur(4px);
        }

        .song-difficulty-badge.hard {
            background: rgba(255, 152, 0, 0.35);
            border: 1px solid rgba(255, 152, 0, 0.55);
        }

        .song-difficulty-badge.expert {
            background: linear-gradient(135deg, rgba(244, 67, 54, 0.35), rgba(233, 30, 99, 0.35));
            border: 1px solid rgba(244, 67, 54, 0.55);
        }

        .song-difficulty-badge.master {
            background: rgba(156, 39, 176, 0.35);
            border: 1px solid rgba(156, 39, 176, 0.55);
        }

        .song-difficulty-badge.append {
            background: linear-gradient(135deg, rgba(156, 39, 176, 0.35), rgba(255, 205, 210, 0.35));
            border: 1px solid rgba(156, 39, 176, 0.55);
        }

        .difficulty-label {
            font-size: 20px;
            font-weight: 800;
            color: white;
            text-shadow: 0 2px 6px rgba(0, 0, 0, 0.5), 0 1px 2px rgba(0, 0, 0, 0.4);
            line-height: 1;
            letter-spacing: 0.5px;
        }

        .difficulty-value {
            font-size: 38px;
            font-weight: 900;
            color: white;
            text-shadow: 0 3px 8px rgba(0, 0, 0, 0.6), 0 1px 4px rgba(0, 0, 0, 0.5);
            line-height: 1;
            letter-spacing: 1px;
        }

        .song-name-left {
            font-size: 26px;
            font-weight: 600;
            color: white;
            text-shadow: 0 2px 10px rgba(0, 0, 0, 0.28), 0 1px 3px rgba(0, 0, 0, 0.18);
            line-height: 1.3;
        }

        .song-name-cn-left {
            font-size: 36px;
            font-weight: 800;
            color: white;
            text-shadow: 0 3px 14px rgba(0, 0, 0, 0.32), 0 1px 3px rgba(0, 0, 0, 0.22);
        }

        .footer {
            margin-top: auto;
            padding-top: 26px;
            font-size: 34px;
            color: rgba(255, 255, 255, 0.88);
            text-shadow: 0 3px 14px rgba(0, 0, 0, 0.32), 0 1px 3px rgba(0, 0, 0, 0.22);
            font-weight: 700;
            letter-spacing: 2.5px;
            line-height: 1.4;
        }

    </style>
</head>
<body>
    <div class="bg-layer"></div>
    <div class="main-wrapper">
        <!-- 左侧面板：原有签到内容 -->
        <div class="left-panel">
            <div class="success-icon">
                <img src="{{b64ok}}" alt="成功" onerror="this.style.display='none'">
            </div>

            <h1>{{name}},签到成功!</h1>
            <div class="date-time" id="datetime">2023年10月15日 14:30</div>

            <div class="fortune-box {{fortune_color}}" id="fortuneBox">
                <div class="fortune-level" id="fortuneLevel">{{fortune_level}}</div>
                <div class="fortune-description" id="fortuneDesc">{{fortune_desc}}</div>
            </div>

            <div class="fortune">
                <div class="fortune-item good">
                    <div class="fortune-icon">
                        <img src="{{b64yi}}" alt="宜" onerror="this.style.display='none'">
                    </div>
                    <div class="fortune-label">宜</div>
                    <div class="fortune-value" id="good">{{yi_text}}</div>
                </div>
                <div class="fortune-item bad">
                    <div class="fortune-icon">
                        <img src="{{b64ji}}" alt="忌" onerror="this.style.display='none'">
                    </div>
                    <div class="fortune-label">忌</div>
                    <div class="fortune-value" id="bad">{{ji_text}}</div>
                </div>
            </div>

            {% if show_song %}
            <!-- 今日推荐歌曲 -->
            <div class="song-section">
                <div class="song-section-title">🎵 今日歌曲推荐</div>
                <div class="song-info-left">
                    <img src="{{song_cover_base64}}" alt="封面" class="song-cover-left" onerror="this.src='data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 100 100%22><rect fill=%22%23667eea%22 width=%22100%22 height=%22100%22/><text x=%2250%22 y=%2255%22 font-size=%2240%22 fill=%22white%22 text-anchor=%22middle%22>🎵</text></svg>'">
                    <div class="song-details-left">
                        <div class="song-name-cn-left">{{song_name_cn}}</div>
                        <div class="song-name-left">{{song_name}}</div>
                    </div>
                    {% if song_difficulty_type %}
                    <div class="song-difficulty-badge {{song_difficulty_type}}">
                        <div class="difficulty-label">{{song_difficulty_label}}</div>
                        <div class="difficulty-value">{{song_difficulty_level}}</div>
                    </div>
                    {% endif %}
                </div>
                <div class="song-info-left song-info-second">
                    <img src="{{song2_cover_base64}}" alt="封面" class="song-cover-left" onerror="this.src='data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 100 100%22><rect fill=%22%23667eea%22 width=%22100%22 height=%22100%22/><text x=%2250%22 y=%2255%22 font-size=%2240%22 fill=%22white%22 text-anchor=%22middle%22>🎵</text></svg>'">
                    <div class="song-details-left">
                        <div class="song-name-cn-left">{{song2_name_cn}}</div>
                        <div class="song-name-left">{{song2_name}}</div>
                    </div>
                    {% if song2_difficulty_type %}
                    <div class="song-difficulty-badge {{song2_difficulty_type}}">
                        <div class="difficulty-label">{{song2_difficulty_label}}</div>
                        <div class="difficulty-value">{{song2_difficulty_level}}</div>
                    </div>
                    {% endif %}
                </div>
            </div>
            {% endif %}

            <div class="footer">
                Designed by 慵懒午睡 | 请勿迷信哦
            </div>
        </div>
        <!-- 右侧面板：留空 -->
        <div class="right-panel">
        </div>
    </div>

    <script>
        function updateDateTime() {
            const now = new Date();
            const options = {
                year: 'numeric',
                month: 'long',
                day: 'numeric',
                hour: '2-digit',
                minute: '2-digit',
                hour12: false,
                timeZone: 'Asia/Shanghai'
            };
            const formattedDate = now.toLocaleString('zh-CN', options);
            document.getElementById('datetime').textContent = formattedDate;
        }

        const goodFortunes = ['追新番', '画同人', '做手书', '参加漫展', '写同人小说', '学习声优', '打游戏', '社区互助','做攻略', '参加社团', '学习绘画', '参加同人展', '分享资源', '关注公益', '练习日语', '整理收藏','看动漫', '听OST', '收集周边', '研究设定', 'cosplay', '配音练习', '剪辑AMV', '制作MAD'];
        const badFortunes = ['沉迷抽卡', '挖坑不填', '刷无用番', '熬夜追更', '沉迷弹幕', '过度氪金', '网暴同好', '弃坑不交', '沉迷游戏','刷无意义弹幕', '过度磕CP', '沉迷虚拟恋爱', '盗版成瘾', '无节制追星', '忽视健康', '网络争吵', '囤积周边','毒唯行为', '引战', '剧透未看番', '滥用表情包', '刷存在感', '跟风黑角色'];

        const fortuneData = [
            { level: '大吉', desc: '最最顺!😎', color: 'good', weight: 5 },
            { level: '吉', desc: '幸福像🎈一样飘起来', color: 'good', weight: 10 },
            { level: '中吉', desc: '努力就发光😋', color: 'good', weight: 15 },
            { level: '小吉', desc: '小小的幸运😆', color: 'good', weight: 20 },
            { level: '半吉', desc: '明天会更开心哦😍', color: 'neutral', weight: 15 },
            { level: '末吉', desc: '转机就在眼前😉', color: 'neutral', weight: 10 },
            { level: '末小吉', desc: '再加把劲哦💪🏻', color: 'neutral', weight: 10 },
            { level: '凶', desc: '困难是成长的礼物🎁', color: 'bad', weight: 8 },
            { level: '小凶', desc: '小心点就好哦❤️', color: 'bad', weight: 7 },
            { level: '半凶', desc: '要小心一点哦..', color: 'bad', weight: 5 },
            { level: '末凶', desc: '要小心一点哦🥺', color: 'bad', weight: 3 },
            { level: '大凶', desc: '要小心一点哦🥺', color: 'bad', weight: 2 }
        ];

        function weightedRandom(items) {
            let totalWeight = 0;
            for (let i = 0; i < items.length; i++) {
                totalWeight += items[i].weight;
            }

            let random = Math.random() * totalWeight;
            let currentWeight = 0;

            for (let i = 0; i < items.length; i++) {
                currentWeight += items[i].weight;
                if (random <= currentWeight) {
                    return items[i];
                }
            }

            return items[items.length - 1];
        }

        function setFortune() {
            const fortuneLevel = document.getElementById('fortuneLevel').textContent.trim();
            const fortuneDesc = document.getElementById('fortuneDesc').textContent.trim();
            
            if (!fortuneLevel || !fortuneDesc) {
                const randomGood = goodFortunes[Math.floor(Math.random() * goodFortunes.length)];
                const randomBad = badFortunes[Math.floor(Math.random() * badFortunes.length)];
                document.getElementById('good').textContent = randomGood;
                document.getElementById('bad').textContent = randomBad;
                
                const selectedFortune = weightedRandom(fortuneData);
                document.getElementById('fortuneLevel').textContent = selectedFortune.level;
                document.getElementById('fortuneDesc').textContent = selectedFortune.desc;

                const fortuneBox = document.getElementById('fortuneBox');
                fortuneBox.className = 'fortune-box ' + selectedFortune.color;
            }
        }

        updateDateTime();
        setFortune();
    </script>
</body>
</html>
"""


@register("astrbot_plugin_signin", "慵懒午睡", "增强版签到插件 - 支持连续签到、歌曲推荐", "2.0.0")


class MyPlugin(Star):
    """增强版签到插件 - 支持连续签到、运势抽取、每日一言、歌曲推荐"""

    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self.config = config

        self.plugin_dir = Path(__file__).parent

        from astrbot.core.utils.astrbot_path import get_astrbot_data_path
        self.data_dir = Path(get_astrbot_data_path()) / "plugin_data" / "astrbot_plugin_signin"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.data_file = self.data_dir / "signin_data.json"
        self.config_file = self.data_dir / "config.json"
        self.db_path = self.data_dir / "signin.db"
        self.img_dir = self.data_dir / "img"
        self.song_dir = self.data_dir / "song"

        # 将插件目录下的默认资源增量同步到持久化目录
        self._sync_plugin_data()

        self._ensure_data_file()
        self._load_custom_config()
        self._load_songs()

        # 初始化SQLite数据库
        self.db = SigninDatabase(self.db_path)

        # 迁移旧数据到新数据库
        try:
            old_data = self._load_data()
            if old_data and isinstance(old_data, dict) and len(old_data) > 0:
                logger.info(f"📦 检测到旧数据格式，开始迁移到SQLite数据库...")
                self.db.migrate_from_json(old_data)
                # 备份旧文件
                backup_file = self.data_file.with_suffix('.json.bak')
                shutil.copy2(self.data_file, backup_file)
                logger.info(f"✅ 数据迁移完成，旧文件已备份为: {backup_file.name}")
        except Exception as e:
            logger.warning(f"⚠️ 数据迁移失败（可忽略）: {e}")

        font_path = self.plugin_dir / "MiSans-Medium.ttf"
        if font_path.exists():
            with open(font_path, 'rb') as f:
                self.base64_font = base64.b64encode(f.read()).decode('utf-8')
            logger.info("✅ 成功加载 MiSans-Medium.ttf 字体")
        else:
            self.base64_font = ""
            logger.warning("⚠️ 未找到 MiSans-Medium.ttf 字体文件，将使用系统默认字体")

        self._load_images_base64()
        self._load_character_metadata()

        logger.info(f"📝 插件配置已加载 - 签到指令: {self.config.get('sign_in_command', '签到')}")

    def _load_character_metadata(self):
        """加载角色元数据，构建名称/别名到目录名的映射"""
        self.character_name_map = {}  # name -> folder_name
        self.character_alias_map = {}  # alias -> folder_name

        chars_file = self.plugin_dir / "characters.json"
        if not chars_file.exists():
            logger.warning("⚠️ 未找到 characters.json，别名搜索不可用")
            return

        try:
            with open(chars_file, 'r', encoding='utf-8') as f:
                characters = json.load(f)

            for char in characters:
                name = char.get('name', '').lower().strip()
                folder = name  # 文件夹名称与 name 一致
                full_name = char.get('fullNameChinese', '').lower().strip()
                aliases = [a.lower().strip() for a in char.get('aliases', [])]

                # 只有该角色目录存在时才加入映射
                if not (self.img_dir / folder).exists():
                    continue

                self.character_name_map[name] = folder
                if full_name:
                    self.character_name_map[full_name] = folder
                for alias in aliases:
                    if alias:
                        self.character_alias_map[alias] = folder

            logger.info(f"✅ 已加载 {len(self.character_name_map)} 个角色名称，{len(self.character_alias_map)} 个别名")
        except Exception as e:
            logger.error(f"❌ 加载 characters.json 失败: {e}")

    def _resolve_character(self, query: str) -> str:
        """根据用户输入的名称或别名解析出角色目录名"""
        query = query.lower().strip()
        if not query:
            return None

        # 直接匹配 name
        if query in self.character_name_map:
            return self.character_name_map[query]

        # 匹配别名
        if query in self.character_alias_map:
            return self.character_alias_map[query]

        # 部分匹配：输入是某个别名的前缀
        for alias, folder in self.character_alias_map.items():
            if alias.startswith(query) or query in alias:
                return folder

        # 部分匹配：输入是 fullNameChinese 的前缀
        for name, folder in self.character_name_map.items():
            if name.startswith(query) or query in name:
                return folder

        return None

    def _sync_plugin_data(self):
        """将插件目录下的默认资源增量同步到持久化目录"""
        plugin_data = self.plugin_dir / "data"
        if not plugin_data.exists():
            return

        for subdir in ["img", "song"]:
            src = plugin_data / subdir
            dst = self.data_dir / subdir
            if not src.exists():
                continue

            if not dst.exists():
                try:
                    shutil.copytree(src, dst)
                    logger.info(f"📦 已同步默认资源 {subdir}/ 到持久化目录")
                except Exception as e:
                    logger.error(f"❌ 同步默认资源 {subdir}/ 失败: {e}")
                continue

            # 增量同步：只复制新增的文件/目录
            for item in src.iterdir():
                dst_item = dst / item.name
                if dst_item.exists():
                    continue
                try:
                    if item.is_dir():
                        shutil.copytree(item, dst_item)
                    else:
                        shutil.copy2(item, dst_item)
                    logger.info(f"📦 增量同步: {subdir}/{item.name}")
                except Exception as e:
                    logger.error(f"❌ 增量同步失败 {item.name}: {e}")

    def _compress_image(self, img_data: bytes, max_size: int = 800, quality: int = 75, fmt: str = "WEBP") -> tuple[str, bytes]:
        """压缩图片：缩放 + 转格式，返回 (mime_type, compressed_bytes)"""
        try:
            img = Image.open(io.BytesIO(img_data))
            # 缩放：保持比例，最长边不超过 max_size
            w, h = img.size
            if max(w, h) > max_size:
                ratio = max_size / max(w, h)
                new_w, new_h = int(w * ratio), int(h * ratio)
                img = img.resize((new_w, new_h), Image.LANCZOS)
            # 转换格式
            if fmt == "WEBP":
                mime = "image/webp"
                save_fmt = "WEBP"
            else:
                mime = "image/jpeg"
                save_fmt = "JPEG"
            buf = io.BytesIO()
            # JPEG 不支持 alpha 通道
            if save_fmt == "JPEG" and img.mode in ("RGBA", "LA", "P"):
                img = img.convert("RGB")
            img.save(buf, format=save_fmt, quality=quality, optimize=True)
            return mime, buf.getvalue()
        except Exception as e:
            logger.warning(f"图片压缩失败，使用原始数据: {e}")
            return None, img_data

    def _image_to_base64(self, img_data: bytes, max_size: int = 800, quality: int = 75, fmt: str = "WEBP") -> str:
        """将图片数据压缩后转为 base64 data URI"""
        mime, compressed = self._compress_image(img_data, max_size, quality, fmt)
        if mime is None:
            # 压缩失败，使用原始数据
            return f"data:image/png;base64,{base64.b64encode(img_data).decode('utf-8')}"
        return f"data:{mime};base64,{base64.b64encode(compressed).decode('utf-8')}"

    def _recompress_image_url(self, url: str, target_kb: int = 100) -> str:
        """对渲染后的图片进行二次压缩，目标大小为 target_kb KB"""
        try:
            # 提取 base64 数据
            if url.startswith("data:"):
                header, b64data = url.split(",", 1)
                img_bytes = base64.b64decode(b64data)
            elif os.path.exists(url):
                with open(url, 'rb') as f:
                    img_bytes = f.read()
            else:
                return url  # URL 格式，无法压缩

            original_kb = len(img_bytes) / 1024
            if original_kb <= target_kb:
                logger.info(f"📦 图片 {original_kb:.1f}KB <= 目标 {target_kb}KB，无需二次压缩")
                return url

            img = Image.open(io.BytesIO(img_bytes))
            if img.mode in ("RGBA", "LA", "P"):
                img = img.convert("RGB")

            # 二分法查找合适的 quality 值
            lo, hi = 10, 85
            result_bytes = img_bytes
            while lo <= hi:
                mid = (lo + hi) // 2
                buf = io.BytesIO()
                img.save(buf, format="JPEG", quality=mid, optimize=True)
                size_kb = buf.tell() / 1024
                if size_kb <= target_kb:
                    result_bytes = buf.getvalue()
                    lo = mid + 1
                else:
                    hi = mid - 1

            # 如果 quality 最低还是太大，缩小尺寸
            final_kb = len(result_bytes) / 1024
            if final_kb > target_kb:
                scale = 0.9
                for _ in range(5):
                    w, h = img.size
                    new_w, new_h = int(w * scale), int(h * scale)
                    resized = img.resize((new_w, new_h), Image.LANCZOS)
                    buf = io.BytesIO()
                    resized.save(buf, format="JPEG", quality=30, optimize=True)
                    result_bytes = buf.getvalue()
                    final_kb = len(result_bytes) / 1024
                    if final_kb <= target_kb:
                        break
                    scale *= 0.9

            final_kb = len(result_bytes) / 1024
            logger.info(f"📦 二次压缩: {original_kb:.1f}KB -> {final_kb:.1f}KB (目标 {target_kb}KB)")
            return f"data:image/jpeg;base64,{base64.b64encode(result_bytes).decode('utf-8')}"
        except Exception as e:
            logger.warning(f"二次压缩失败，使用原始图片: {e}")
            return url

    def _load_images_base64(self):
        """按人物加载图片资源，每个人物包含 ok/yi/ji 图片和卡面背景"""
        self.character_images = {}
        self.character_cards = {}

        # 动态扫描 img 目录下的所有子目录作为角色
        if self.img_dir.exists():
            self.characters = [
                d.name for d in self.img_dir.iterdir()
                if d.is_dir() and (d / "ok.png").exists()
            ]
        else:
            self.characters = []

        for char in self.characters:
            char_dir = self.img_dir / char
            if not char_dir.exists():
                logger.warning(f"⚠️ 人物目录不存在: {char_dir}")
                continue

            self.character_images[char] = {}
            img_files = {
                'ok': char_dir / "ok.png",
                'yi': char_dir / "yi.png",
                'ji': char_dir / "ji.png"
            }

            for name, path in img_files.items():
                if path.exists():
                    try:
                        with open(path, 'rb') as f:
                            img_data = f.read()
                            self.character_images[char][name] = self._image_to_base64(img_data, max_size=300, quality=55, fmt="WEBP")
                        logger.info(f"✅ 成功加载图片: {char}/{path.name}")
                    except Exception as e:
                        logger.error(f"❌ 加载图片失败 {char}/{path.name}: {e}")
                        self.character_images[char][name] = ""
                else:
                    logger.warning(f"⚠️ 图片文件不存在: {path}")
                    self.character_images[char][name] = ""

            cards = []
            for card_file in char_dir.iterdir():
                if card_file.suffix.lower() in ['.png', '.jpg', '.jpeg', '.webp'] and card_file.name not in ['ok.png', 'yi.png', 'ji.png']:
                    cards.append(card_file)
            self.character_cards[char] = cards
            logger.info(f"✅ 加载人物 {char} 背景卡图 {len(cards)} 张")

        total_cards = sum(len(cards) for cards in self.character_cards.values())
        logger.info(f"✅ 共加载 {len(self.character_images)} 个人物，{total_cards} 张背景卡图")

    def _select_random_character(self):
        """从可用角色中随机选择一位"""
        available = [c for c in self.characters if c in self.character_images and c in self.character_cards]
        if not available:
            return None
        return _secure_random_choice(available)

    def _get_character_images(self, character):
        """获取指定人物的 ok/yi/ji 图片"""
        return self.character_images.get(character, {})

    def _get_random_bg(self, character):
        """从指定人物的卡面资源中随机选择一张背景卡图并转为base64（不压缩，保持原画质）"""
        cards = self.character_cards.get(character, [])
        if not cards:
            return ""

        card = _secure_random_choice(cards)
        if card is None:
            return ""

        try:
            with open(card, 'rb') as f:
                img_data = f.read()
                suffix = card.suffix.lower()
                if suffix == '.webp':
                    mime = 'image/webp'
                elif suffix in ['.jpg', '.jpeg']:
                    mime = 'image/jpeg'
                else:
                    mime = 'image/png'
                return f"data:{mime};base64,{base64.b64encode(img_data).decode('utf-8')}"
        except Exception as e:
            logger.error(f"❌ 加载背景卡图失败 {card.name}: {e}")
            return ""

    def _ensure_data_file(self):
        if not self.data_file.exists():
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump({}, f)

    def _load_custom_config(self):
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    self.custom_config = json.load(f)
                logger.info("✅ 成功加载自定义配置文件")
            else:
                self.custom_config = {
                    "daily_quotes": ["每一天都是新的开始，加油！"],
                    "song_descriptions": {}
                }
                logger.warning("⚠️ 未找到自定义配置文件，使用默认配置")
        except Exception as e:
            logger.error(f"加载自定义配置文件失败: {e}")
            self.custom_config = {"daily_quotes": ["每一天都是新的开始，加油！"], "song_descriptions": {}}

    def _load_songs(self):
        try:
            songs_file = self.song_dir / "songs.json"
            if songs_file.exists():
                with open(songs_file, 'r', encoding='utf-8') as f:
                    self.songs = json.load(f)
                logger.info(f"✅ 成功加载歌曲库，共 {len(self.songs)} 首歌曲")
            else:
                self.songs = []
                logger.warning("⚠️ 未找到歌曲数据库")
        except Exception as e:
            logger.error(f"加载歌曲数据失败: {e}")
            self.songs = []

    def _load_data(self):
        try:
            if not self.data_file.exists():
                return {}
            with open(self.data_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"加载签到数据失败: {e}")
            return {}

    def _save_data(self, data):
        try:
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except IOError as e:
            logger.error(f"保存签到数据失败: {e}")

    def _get_context_id(self, event):
        """只使用用户ID作为上下文标识，不再区分群聊/私聊"""
        try:
            user_id = event.get_sender_id()
            if user_id:
                return f"user_{user_id}"
            return "default_ctx"
        except Exception as e:
            logger.warning(f"获取上下文ID失败: {e}")
            return "default_ctx"

    def _is_signed_in_today(self, ctx_id, user_id):
        data = self._load_data()
        today = datetime.now().strftime("%Y-%m-%d")
        ctx_data = data.get(ctx_id, {})
        user_data = ctx_data.get(user_id, {})
        return user_data.get("last_checkin") == today

    def _get_user_data_safe(self, ctx_id, user_id):
        """安全获取用户数据，自动处理旧格式和异常情况"""
        try:
            data = self._load_data()
            if not isinstance(data, dict):
                logger.warning(f"数据文件格式异常，正在重置: {type(data)}")
                return {}

            ctx_data = data.get(ctx_id, {})
            if not isinstance(ctx_data, dict):
                logger.warning(f"上下文数据格式异常: {ctx_id}")
                return {}

            user_data = ctx_data.get(user_id, {})
            if not isinstance(user_data, dict):
                logger.warning(f"用户数据格式异常: {user_id}")
                return {}

            return user_data

        except Exception as e:
            logger.error(f"获取用户数据失败: {e}")
            return {}

    def _migrate_old_data(self, ctx_id, user_id):
        """迁移旧版数据格式，确保包含 checkin_history 字段"""
        try:
            data = self._load_data()

            if ctx_id not in data:
                return

            if user_id not in data[ctx_id]:
                return

            user_data = data[ctx_id][user_id]

            if not isinstance(user_data, dict):
                data[ctx_id][user_id] = {
                    "username": str(user_data),
                    "last_checkin": None,
                    "checkin_history": []
                }
                self._save_data(data)
                logger.info(f"已迁移用户数据格式: {user_id}")
                return

            if "checkin_history" not in user_data:
                last_checkin = user_data.get("last_checkin")

                if last_checkin:
                    user_data["checkin_history"] = [last_checkin]
                    logger.info(f"从 last_checkin 迁移历史记录: {user_id} → [{last_checkin}]")
                else:
                    user_data["checkin_history"] = []

                self._save_data(data)

        except Exception as e:
            logger.error(f"数据迁移失败: {e}")

    def _calculate_streak(self, ctx_id, user_id):
        """计算用户连续签到天数"""
        self._migrate_old_data(ctx_id, user_id)

        user_data = self._get_user_data_safe(ctx_id, user_id)
        checkin_history = user_data.get("checkin_history", [])

        if not checkin_history or not isinstance(checkin_history, list):
            return 0

        streak = 0
        today = datetime.now().date()

        for i in range(len(checkin_history)):
            expected_date = today - timedelta(days=i)
            expected_str = expected_date.strftime("%Y-%m-%d")
            if expected_str in checkin_history:
                streak += 1
            else:
                break

        return streak

    def _get_signed_dates_this_month(self, ctx_id, user_id):
        """获取本月已签到的日期列表"""
        self._migrate_old_data(ctx_id, user_id)

        user_data = self._get_user_data_safe(ctx_id, user_id)
        checkin_history = user_data.get("checkin_history", [])

        if not isinstance(checkin_history, list):
            logger.warning(f"checkin_history 格式异常: {type(checkin_history)}")
            return []

        today = datetime.now()
        current_month = today.strftime("%Y-%m")

        signed_dates = []
        for date_str in checkin_history:
            if isinstance(date_str, str) and date_str.startswith(current_month):
                try:
                    day = int(date_str.split("-")[2])
                    signed_dates.append(day)
                except (ValueError, IndexError) as e:
                    logger.warning(f"日期格式错误: {date_str} - {e}")

        return signed_dates

    def _record_signin(self, ctx_id, user_id, user_name):
        try:
            data = self._load_data()
            today = datetime.now().strftime("%Y-%m-%d")

            if not isinstance(data, dict):
                logger.error(f"数据格式异常，无法记录签到")
                return

            if ctx_id not in data:
                data[ctx_id] = {}

            if user_id not in data[ctx_id]:
                data[ctx_id][user_id] = {
                    "username": user_name,
                    "last_checkin": None,
                    "checkin_history": []
                }

            user_data = data[ctx_id][user_id]
            if not isinstance(user_data, dict):
                data[ctx_id][user_id] = {
                    "username": user_name,
                    "last_checkin": None,
                    "checkin_history": []
                }
                user_data = data[ctx_id][user_id]

            user_data["username"] = user_name
            user_data["last_checkin"] = today

            if "checkin_history" not in user_data or not isinstance(user_data["checkin_history"], list):
                user_data["checkin_history"] = []

            if today not in user_data["checkin_history"]:
                user_data["checkin_history"].append(today)

            self._save_data(data)
            logger.info(f"✅ 签到记录已保存: {user_name}({user_id}) @ {ctx_id}")

        except Exception as e:
            logger.error(f"❌ 保存签到记录失败: {e}")

    def _get_random_song(self):
        """使用难度相似性算法选择两首歌曲"""
        if not self.songs:
            return [
                {"name": "暂无歌曲", "name_cn": "暂无歌曲", "cover_base64": "", 
                 "difficulty_type": None, "difficulty_level": None, "difficulty_label": None},
                {"name": "暂无歌曲", "name_cn": "暂无歌曲", "cover_base64": "",
                 "difficulty_type": None, "difficulty_level": None, "difficulty_label": None}
            ]

        selected_songs = select_song_with_difficulty(self.songs)

        if len(selected_songs) < 2:
            selected_songs = selected_songs + [selected_songs[0] if selected_songs else None] * (2 - len(selected_songs))

        result = []
        for song in selected_songs[:2]:
            if song is None:
                result.append({"name": "暂无歌曲", "name_cn": "暂无歌曲", "cover_base64": "",
                               "difficulty_type": None, "difficulty_level": None, "difficulty_label": None})
                continue

            song_id = str(song.get("id", ""))

            cover_path = None
            used_ext = ".webp"
            for ext in [".webp", ".png", ".jpg", ".jpeg"]:
                test_path = self.song_dir / "images" / f"{song_id}{ext}"
                if test_path.exists():
                    cover_path = test_path
                    used_ext = ext
                    break

            cover_base64 = ""
            if cover_path:
                try:
                    with open(cover_path, 'rb') as f:
                        img_data = f.read()
                        cover_base64 = self._image_to_base64(img_data, max_size=200, quality=50, fmt="WEBP")
                except Exception as e:
                    logger.warning(f"加载歌曲封面失败: {cover_path} - {e}")

            cn = song.get("cn", "")
            jp = song.get("n", "未知")
            composer = song.get("composer", "")

            display_name = f"{cn}" if cn else f"{jp}"

            result.append({
                "name": composer,
                "name_cn": display_name,
                "id": song_id,
                "cover_base64": cover_base64,
                "difficulty_type": song.get("difficulty_type"),
                "difficulty_level": song.get("difficulty_level"),
                "difficulty_label": song.get("difficulty_label")
            })

        while len(result) < 2:
            result.append({"name": "", "name_cn": "暂无歌曲", "cover_base64": "",
                           "difficulty_type": None, "difficulty_level": None, "difficulty_label": None})

        return result

    def _generate_fortune(self) -> dict:
        """生成每日运势"""
        fortune_data = [
            { 'level': '大吉', 'desc': '最最顺!😎', 'color': 'good', 'weight': 5 },
            { 'level': '吉', 'desc': '幸福像🎈一样飘起来', 'color': 'good', 'weight': 10 },
            { 'level': '中吉', 'desc': '努力就发光😋', 'color': 'good', 'weight': 15 },
            { 'level': '小吉', 'desc': '小小的幸运😆', 'color': 'good', 'weight': 20 },
            { 'level': '半吉', 'desc': '明天会更开心哦😍', 'color': 'neutral', 'weight': 15 },
            { 'level': '末吉', 'desc': '转机就在眼前😉', 'color': 'neutral', 'weight': 10 },
            { 'level': '末小吉', 'desc': '再加把劲哦💪🏻', 'color': 'neutral', 'weight': 10 },
            { 'level': '凶', 'desc': '困难是成长的礼物🎁', 'color': 'bad', 'weight': 8 },
            { 'level': '小凶', 'desc': '小心点就好哦❤️', 'color': 'bad', 'weight': 7 },
            { 'level': '半凶', 'desc': '要小心一点哦..', 'color': 'bad', 'weight': 5 },
            { 'level': '末凶', 'desc': '要小心一点哦🥺', 'color': 'bad', 'weight': 3 },
            { 'level': '大凶', 'desc': '要小心一点哦🥺', 'color': 'bad', 'weight': 2 }
        ]
        return self._weighted_random(fortune_data)

    def _weighted_random(self, items) -> dict:
        total_weight = sum(item['weight'] for item in items)
        random_val = random.random() * total_weight
        current_weight = 0
        for item in items:
            current_weight += item['weight']
            if random_val <= current_weight:
                return item
        return items[-1]

    def _get_yi_activity(self) -> str:
        """获取宜活动"""
        good_fortunes = [
            '追新番', '画同人', '做手书', '参加漫展', '写同人小说', '学习声优', '打游戏', '社区互助',
            '做攻略', '参加社团', '学习绘画', '参加同人展', '分享资源', '关注公益', '练习日语', '整理收藏',
            '看动漫', '听OST', '收集周边', '研究设定', 'cosplay', '配音练习', '剪辑AMV',
            '早起锻炼', '阅读好书', '整理房间', '学习新技能', '写日记', '拍照记录', '打歌',
            '冲榜', '陪伴家人', '户外散步', '听音乐', '练习乐器', '烘焙甜点', '种植花草',
            '练习书法', '拼图游戏', '整理相册', '尝试新餐厅',
            '给好友写信', '制定计划', '跑步运动',
            '参观博物馆', '逛书店', '手工DIY', '整理衣橱', '学习摄影',
            '看演唱会', '参加读书会', '整理笔记',
            '做志愿者', '学习舞蹈', '玩桌游'
            '学习烹饪', '品咖啡', '逛花市', '看日出',
            '整理音乐列表',
            '写短篇小说', '学习插花', '制作手账', '学习滑板', '放风筝'
        ]
        return random.choice(good_fortunes)

    def _get_ji_activity(self) -> str:
        """获取忌活动"""
        bad_fortunes = [
            '沉迷抽卡', '挖坑不填', '刷无用番', '熬夜追更', '沉迷弹幕', '过度氪金', '网暴同好', '弃坑不交', '沉迷游戏',
            '刷无意义弹幕', '过度磕CP', '沉迷虚拟恋爱', '盗版成瘾', '无节制追星', '忽视健康', '网络争吵', '囤积周边',
            '毒唯行为', '引战', '剧透未看番', '滥用表情包', '刷存在感', '跟风黑角色'
        ]
        return random.choice(bad_fortunes)

    @filter.event_message_type(filter.EventMessageType.GROUP_MESSAGE | filter.EventMessageType.PRIVATE_MESSAGE)
    async def listen_signin(self, event: AstrMessageEvent):
        message_text = event.message_str.strip()
        sign_in_cmd = self.config.get('sign_in_command', '签到')

        is_test = message_text == "测试签到"
        char_query = ""

        if not is_test:
            if not message_text.startswith(sign_in_cmd):
                return
            # 提取角色名参数，如 "签到 ena" 或 "签到 彰人"
            char_query = message_text[len(sign_in_cmd):].strip()

        # 解析指定角色
        specified_character = None
        if char_query:
            specified_character = self._resolve_character(char_query)
            if specified_character:
                logger.info(f"🎯 用户指定角色: {char_query} -> {specified_character}")
            else:
                logger.warning(f"⚠️ 未找到角色: {char_query}，静默忽略")
                return

        user_id = event.get_sender_id()
        user_name = event.get_sender_name()
        ctx_id = self._get_context_id(event)

        if not user_id or not user_name:
            logger.warning(f"无法获取用户信息: user_id={user_id}, user_name={user_name}")
            return

        streak_days = 1
        signed_dates = []
        
        if not is_test:
            today = datetime.now().strftime("%Y-%m-%d")

            try:
                self.db.record_checkin(ctx_id, user_id, user_name)
            except Exception as e:
                logger.error(f"❌ 数据库记录签到失败: {e}")
                self._record_signin(ctx_id, user_id, user_name)

            logger.info(f"用户 {user_name}({user_id}) 在 {ctx_id} 签到成功")
        else:
            logger.info(f"用户 {user_name}({user_id}) 在 {ctx_id} 测试签到（不记录，不使用持久化状态）")

        if not is_test:
            try:
                user_stats = self.db.get_user_stats(ctx_id, user_id)
                streak_days = user_stats.get('streak', 0)
            except Exception as e:
                logger.warning(f"从数据库获取连续签到天数失败: {e}，使用旧方法")
                streak_days = self._calculate_streak(ctx_id, user_id)

            try:
                signed_dates = user_stats.get('signed_dates', []) if self.config.get('show_calendar', True) else []
            except Exception as e:
                logger.warning(f"获取签到日期失败: {e}，使用旧方法")
                signed_dates = self._get_signed_dates_this_month(ctx_id, user_id)

        existing_daily_state = None
        if not is_test:
            existing_daily_state = self.db.get_daily_state(ctx_id, user_id)

        fortune_data = None
        songs = None

        if existing_daily_state:
            fortune_data = {
                'level': existing_daily_state.get('fortune_level', ''),
                'desc': existing_daily_state.get('fortune_desc', ''),
                'color': existing_daily_state.get('fortune_color', 'neutral')
            }
            yi_text = existing_daily_state.get('yi_activity', '') or self._get_yi_activity()
            ji_text = existing_daily_state.get('ji_activity', '') or self._get_ji_activity()
            songs = [
                {
                    "name": existing_daily_state.get('song1_name', ''),
                    "name_cn": existing_daily_state.get('song1_name_cn', ''),
                    "cover_base64": existing_daily_state.get('song1_cover_base64', ''),
                    "difficulty_type": existing_daily_state.get('song1_difficulty_type', ''),
                    "difficulty_level": existing_daily_state.get('song1_difficulty_level', 0),
                    "difficulty_label": existing_daily_state.get('song1_difficulty_label', '')
                },
                {
                    "name": existing_daily_state.get('song2_name', ''),
                    "name_cn": existing_daily_state.get('song2_name_cn', ''),
                    "cover_base64": existing_daily_state.get('song2_cover_base64', ''),
                    "difficulty_type": existing_daily_state.get('song2_difficulty_type', ''),
                    "difficulty_level": existing_daily_state.get('song2_difficulty_level', 0),
                    "difficulty_label": existing_daily_state.get('song2_difficulty_label', '')
                }
            ]
            logger.info(f"📦 使用已保存的每日签到状态: {user_name}({user_id})")
        else:
            fortune_data = self._generate_fortune()
            yi_text = self._get_yi_activity()
            ji_text = self._get_ji_activity()

            try:
                songs = self._get_random_song() if self.config.get('show_song_recommendation', True) else None
            except Exception as e:
                logger.warning(f"获取推荐歌曲失败: {e}")
                songs = None

        # 选择角色：用户指定 > 随机
        if specified_character and specified_character in self.character_images:
            character = specified_character
            logger.info(f"🎭 使用指定角色: {character}")
        else:
            character = self._select_random_character()

        if not character:
            logger.error("❌ 无法选择有效人物，请检查图片资源目录")
            yield event.plain_result("⚠️ 签到失败：图片资源加载异常，请联系管理员")
            return

        char_images = self._get_character_images(character)
        bg_base64 = self._get_random_bg(character)

        if not is_test and not existing_daily_state:
            if fortune_data:
                state_data = {
                    'fortune_level': fortune_data.get('level', ''),
                    'fortune_desc': fortune_data.get('desc', ''),
                    'fortune_color': fortune_data.get('color', 'neutral'),
                    'yi_activity': yi_text,
                    'ji_activity': ji_text,
                    'song1_name': songs[0].get('name', '') if songs and len(songs) > 0 else '',
                    'song1_name_cn': songs[0].get('name_cn', '') if songs and len(songs) > 0 else '',
                    'song1_cover_base64': songs[0].get('cover_base64', '') if songs and len(songs) > 0 else '',
                    'song1_difficulty_type': songs[0].get('difficulty_type', '') if songs and len(songs) > 0 else '',
                    'song1_difficulty_level': songs[0].get('difficulty_level', 0) if songs and len(songs) > 0 else 0,
                    'song1_difficulty_label': songs[0].get('difficulty_label', '') if songs and len(songs) > 0 else '',
                    'song2_name': songs[1].get('name', '') if songs and len(songs) > 1 else '',
                    'song2_name_cn': songs[1].get('name_cn', '') if songs and len(songs) > 1 else '',
                    'song2_cover_base64': songs[1].get('cover_base64', '') if songs and len(songs) > 1 else '',
                    'song2_difficulty_type': songs[1].get('difficulty_type', '') if songs and len(songs) > 1 else '',
                    'song2_difficulty_level': songs[1].get('difficulty_level', 0) if songs and len(songs) > 1 else 0,
                    'song2_difficulty_label': songs[1].get('difficulty_label', '') if songs and len(songs) > 1 else ''
                }
                try:
                    self.db.save_daily_state(ctx_id, user_id, user_name, state_data)
                except Exception as e:
                    logger.error(f"❌ 保存每日签到状态失败: {e}")

        ui_settings = self.config.get('ui_settings', {})

        options = {
            "quality": 30,
            "device_scale_factor_level": "high",
            "full_page": True,
            "omit_background": False,
            "type": "jpeg",
            "viewport": {"width": 800, "height": 720}
        }

        song1 = songs[0] if songs and len(songs) >= 1 else {"name": "", "name_cn": "名称：未知歌曲", "cover_base64": "", "difficulty_type": None, "difficulty_level": None, "difficulty_label": None}
        song2 = songs[1] if songs and len(songs) >= 2 else {"name": "", "name_cn": "名称：未知歌曲", "cover_base64": "", "difficulty_type": None, "difficulty_level": None, "difficulty_label": None}

        try:
            render_data = {
                "name": user_name or "用户",
                "base64_font": getattr(self, 'base64_font', ''),
                "b64bg": bg_base64,
                "b64ok": char_images.get('ok', ''),
                "b64yi": char_images.get('yi', ''),
                "b64ji": char_images.get('ji', ''),
                "fortune_level": fortune_data.get('level', '') if fortune_data else '',
                "fortune_desc": fortune_data.get('desc', '') if fortune_data else '',
                "fortune_color": fortune_data.get('color', 'neutral') if fortune_data else 'neutral',
                "yi_text": yi_text,
                "ji_text": ji_text,
                "streak_days": max(1, streak_days),
                "signed_dates": signed_dates or [],
                "song_name": song1.get("name", ""),
                "song_name_cn": song1.get("name_cn", "名称：未知歌曲"),
                "song_cover_base64": song1.get("cover_base64", ""),
                "song_difficulty_type": song1.get("difficulty_type") or "",
                "song_difficulty_level": song1.get("difficulty_level") or "",
                "song_difficulty_label": song1.get("difficulty_label") or "",
                "song2_name": song2.get("name", ""),
                "song2_name_cn": song2.get("name_cn", "名称：未知歌曲"),
                "song2_cover_base64": song2.get("cover_base64", ""),
                "song2_difficulty_type": song2.get("difficulty_type") or "",
                "song2_difficulty_level": song2.get("difficulty_level") or "",
                "song2_difficulty_label": song2.get("difficulty_label") or "",
                "show_song": bool(self.config.get('show_song_recommendation', True)),
                "card_opacity": float(ui_settings.get('card_opacity', 0.22)) if isinstance(ui_settings, dict) else 0.22,
                "blur_intensity": int(ui_settings.get('blur_intensity', 26)) if isinstance(ui_settings, dict) else 26,
                "footer_text": self.config.get('footer_text', 'mzkbot by 慵懒午睡 | 请勿迷信哦🥺')
            }

            url = await self.html_render(TMPL, render_data, options=options)

            # 二次压缩：确保最终图片在 100KB 左右
            url = self._recompress_image_url(url, target_kb=100)

            yield event.image_result(url)
        except Exception as e:
            error_type = type(e).__name__
            logger.error(f"❌ 渲染签到卡片失败 [{error_type}]: {e}")
            import traceback
            logger.error(f"堆栈信息:\n{traceback.format_exc()}")
            yield event.plain_result(
                self._build_text_signin(
                    user_name, fortune_data, yi_text, ji_text,
                    songs, streak_days, signed_dates, character
                )
            )

    def _build_text_signin(self, user_name, fortune_data, yi_text, ji_text,
                           songs, streak_days, signed_dates, character):
        """图片渲染失败时，构建文字版签到内容"""
        lines = []
        lines.append(f"🎉 {user_name}，签到成功！")

        if fortune_data:
            level = fortune_data.get('level', '未知')
            desc = fortune_data.get('desc', '')
            lines.append(f"✨ 今日运势：{level} {desc}")

        if yi_text:
            lines.append(f"✅ 宜：{yi_text}")
        if ji_text:
            lines.append(f"❌ 忌：{ji_text}")

        if songs and len(songs) > 0:
            lines.append("🎵 今日歌曲推荐：")
            for i, song in enumerate(songs[:2], 1):
                name_cn = song.get('name_cn', '')
                name = song.get('name', '')
                diff_type = song.get('difficulty_type', '')
                diff_level = song.get('difficulty_level', '')
                diff_label = song.get('difficulty_label', '')
                if name_cn or name:
                    song_line = f"  {i}. {name_cn or name}"
                    if diff_type and diff_level:
                        song_line += f" [{diff_label or diff_type.upper()}{diff_level}]"
                    lines.append(song_line)

        return "\n".join(lines)

    async def terminate(self):
        # 关闭数据库连接
        if hasattr(self, 'db'):
            try:
                self.db.close()
                logger.info("✅ SQLite数据库连接已关闭")
            except Exception as e:
                logger.warning(f"关闭数据库连接失败: {e}")
        logger.info("增强版签到插件已停止")


class SigninDatabase:
    """SQLite 数据库管理器 - 高性能签到数据存储"""
    
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._local = threading.local()
        self._lock = threading.Lock()
        self._init_database()
        logger.info(f"✅ SQLite 数据库初始化完成: {db_path.name}")

    def _get_conn(self) -> sqlite3.Connection:
        if not hasattr(self._local, 'conn') or self._local.conn is None:
            self._local.conn = sqlite3.connect(
                str(self.db_path),
                check_same_thread=False,
                timeout=10
            )
            self._local.conn.row_factory = sqlite3.Row
            self._local.conn.execute("PRAGMA journal_mode=WAL")
            self._local.conn.execute("PRAGMA synchronous=NORMAL")
            self._local.conn.execute("PRAGMA cache_size=-64000")
        return self._local.conn

    def _init_database(self):
        with self._get_conn() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ctx_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    username TEXT DEFAULT '',
                    last_checkin TEXT,
                    total_checkins INTEGER DEFAULT 0,
                    max_streak INTEGER DEFAULT 0,
                    current_streak INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(ctx_id, user_id)
                );

                CREATE TABLE IF NOT EXISTS checkin_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_ref INTEGER NOT NULL,
                    checkin_date TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_ref) REFERENCES users(id),
                    UNIQUE(user_ref, checkin_date)
                );

                CREATE TABLE IF NOT EXISTS daily_signin_state (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_ref INTEGER NOT NULL,
                    signin_date TEXT NOT NULL,
                    fortune_level TEXT,
                    fortune_desc TEXT,
                    fortune_color TEXT,
                    yi_activity TEXT,
                    ji_activity TEXT,
                    song1_name TEXT,
                    song1_name_cn TEXT,
                    song1_cover_base64 TEXT,
                    song1_difficulty_type TEXT,
                    song1_difficulty_level INTEGER,
                    song1_difficulty_label TEXT,
                    song2_name TEXT,
                    song2_name_cn TEXT,
                    song2_cover_base64 TEXT,
                    song2_difficulty_type TEXT,
                    song2_difficulty_level INTEGER,
                    song2_difficulty_label TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_ref) REFERENCES users(id),
                    UNIQUE(user_ref, signin_date)
                );

                CREATE INDEX IF NOT EXISTS idx_checkin_date 
                    ON checkin_history(checkin_date);
                
                CREATE INDEX IF NOT EXISTS idx_user_ctx 
                    ON users(ctx_id, user_id);

                CREATE INDEX IF NOT EXISTS idx_daily_state_date 
                    ON daily_signin_state(user_ref, signin_date);
            """)
            conn.commit()

    def migrate_from_json(self, json_data: dict):
        from datetime import datetime
        for ctx_id, users in json_data.items():
            for user_id, user_data in users.items():
                if not isinstance(user_data, dict):
                    continue
                
                username = user_data.get('username', 'Unknown')
                last_checkin = user_data.get('last_checkin')
                history = user_data.get('checkin_history', [])
                
                try:
                    with self._get_conn() as conn:
                        cursor = conn.execute(
                            "INSERT OR IGNORE INTO users (ctx_id, user_id, username, last_checkin) VALUES (?, ?, ?, ?)",
                            (ctx_id, user_id, username, last_checkin)
                        )
                        user_ref = cursor.lastrowid
                        
                        if history and isinstance(history, list):
                            for date_str in history:
                                conn.execute(
                                    "INSERT OR IGNORE INTO checkin_history (user_ref, checkin_date) VALUES (?, ?)",
                                    (user_ref, date_str)
                                )
                        
                        conn.commit()
                except Exception as e:
                    logger.warning(f"迁移数据失败: {user_id} - {e}")

    def get_or_create_user(self, ctx_id: str, user_id: str, username: str = "") -> dict:
        with self._get_conn() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO users (ctx_id, user_id, username) VALUES (?, ?, ?)",
                (ctx_id, user_id, username)
            )
            
            row = conn.execute(
                "SELECT * FROM users WHERE ctx_id = ? AND user_id = ?",
                (ctx_id, user_id)
            ).fetchone()
            
            if row and row['username'] != username:
                conn.execute(
                    "UPDATE users SET username = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                    (username, row['id'])
                )
                conn.commit()
            
            return dict(row) if row else {}

    def record_checkin(self, ctx_id: str, user_id: str, username: str) -> bool:
        today = datetime.now().strftime("%Y-%m-%d")
        
        with self._get_conn() as conn:
            user = self.get_or_create_user(ctx_id, user_id, username)
            
            if not user:
                return False
            
            existing = conn.execute(
                "SELECT id FROM checkin_history WHERE user_ref = ? AND checkin_date = ?",
                (user['id'], today)
            ).fetchone()
            
            if existing:
                return False
            
            conn.execute(
                "INSERT INTO checkin_history (user_ref, checkin_date) VALUES (?, ?)",
                (user['id'], today)
            )
            
            streak = self._calculate_streak(user['id'])
            total = conn.execute(
                "SELECT COUNT(*) FROM checkin_history WHERE user_ref = ?", 
                (user['id'],)
            ).fetchone()[0]
            
            max_streak = self._calculate_max_streak(user['id'])
            
            conn.execute("""
                UPDATE users SET 
                    last_checkin = ?,
                    total_checkins = ?,
                    current_streak = ?,
                    max_streak = MAX(max_streak, ?),
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (today, total, streak, max_streak, streak, user['id']))
            
            conn.commit()
            logger.info(f"✅ 签到记录已保存到数据库: {username}({user_id}) @ {ctx_id}")
            return True

    def _calculate_streak(self, user_id: int) -> int:
        with self._get_conn() as conn:
            dates = sorted([
                r[0] for r in conn.execute(
                    "SELECT checkin_date FROM checkin_history WHERE user_ref = ? ORDER BY checkin_date DESC LIMIT 365",
                    (user_id,)
                ).fetchall()
            ], reverse=True)
            
            if not dates:
                return 0
            
            streak = 0
            today = datetime.now().date()
            
            for i in range(len(dates)):
                expected = (today - timedelta(days=i)).strftime("%Y-%m-%d")
                if expected in dates:
                    streak += 1
                else:
                    break
            
            return streak

    def _calculate_max_streak(self, user_id: int) -> int:
        with self._get_conn() as conn:
            dates = sorted([r[0] for r in conn.execute(
                "SELECT checkin_date FROM checkin_history WHERE user_ref = ? ORDER BY checkin_date ASC",
                (user_id,)
            ).fetchall()])
            
            if not dates:
                return 0
            
            max_streak = 1
            current_streak = 1
            
            for i in range(1, len(dates)):
                prev = datetime.strptime(dates[i-1], "%Y-%m-%d").date()
                curr = datetime.strptime(dates[i], "%Y-%m-%d").date()
                
                if (curr - prev).days == 1:
                    current_streak += 1
                    max_streak = max(max_streak, current_streak)
                else:
                    current_streak = 1
            
            return max_streak

    def get_user_stats(self, ctx_id: str, user_id: str) -> dict:
        user = self.get_or_create_user(ctx_id, user_id)
        
        if not user:
            return {
                'streak': 0,
                'total': 0,
                'max_streak': 0,
                'signed_dates': [],
                'is_signed_today': False
            }
        
        today = datetime.now().strftime("%Y-%m-%d")
        
        with self._get_conn() as conn:
            is_signed = conn.execute(
                "SELECT id FROM checkin_history WHERE user_ref = ? AND checkin_date = ?",
                (user['id'], today)
            ).fetchone() is not None
            
            signed_dates = [
                int(r[0].split("-")[2]) for r in conn.execute(
                    "SELECT checkin_date FROM checkin_history WHERE user_ref = ? AND checkin_date LIKE ? ORDER BY checkin_date",
                    (user['id'], f"{datetime.now().strftime('%Y-%m')}%")
                ).fetchall() if r[0]
            ]
            
            return {
                'streak': user.get('current_streak', 0) + (1 if is_signed else 0),
                'total': user.get('total_checkins', 0) + (1 if is_signed else 0),
                'max_streak': user.get('max_streak', 0),
                'signed_dates': signed_dates,
                'is_signed_today': is_signed
            }

    def save_daily_state(self, ctx_id: str, user_id: str, username: str, state_data: dict) -> bool:
        today = datetime.now().strftime("%Y-%m-%d")
        
        with self._get_conn() as conn:
            user = self.get_or_create_user(ctx_id, user_id, username)
            
            if not user:
                return False
            
            conn.execute("""
                INSERT OR REPLACE INTO daily_signin_state 
                    (user_ref, signin_date, fortune_level, fortune_desc, fortune_color, 
                     yi_activity, ji_activity, 
                     song1_name, song1_name_cn, song1_cover_base64,
                     song1_difficulty_type, song1_difficulty_level, song1_difficulty_label,
                     song2_name, song2_name_cn, song2_cover_base64,
                     song2_difficulty_type, song2_difficulty_level, song2_difficulty_label,
                     updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (
                user['id'], today,
                state_data.get('fortune_level', ''),
                state_data.get('fortune_desc', ''),
                state_data.get('fortune_color', 'neutral'),
                state_data.get('yi_activity', ''),
                state_data.get('ji_activity', ''),
                state_data.get('song1_name', ''),
                state_data.get('song1_name_cn', ''),
                state_data.get('song1_cover_base64', ''),
                state_data.get('song1_difficulty_type', ''),
                state_data.get('song1_difficulty_level', 0),
                state_data.get('song1_difficulty_label', ''),
                state_data.get('song2_name', ''),
                state_data.get('song2_name_cn', ''),
                state_data.get('song2_cover_base64', ''),
                state_data.get('song2_difficulty_type', ''),
                state_data.get('song2_difficulty_level', 0),
                state_data.get('song2_difficulty_label', '')
            ))
            
            conn.commit()
            logger.info(f"✅ 每日签到状态已保存: {username}({user_id}) @ {ctx_id}")
            return True

    def get_daily_state(self, ctx_id: str, user_id: str) -> dict:
        today = datetime.now().strftime("%Y-%m-%d")
        
        with self._get_conn() as conn:
            user = self.get_or_create_user(ctx_id, user_id)
            
            if not user:
                return None
            
            row = conn.execute(
                "SELECT * FROM daily_signin_state WHERE user_ref = ? AND signin_date = ?",
                (user['id'], today)
            ).fetchone()
            
            if not row:
                return None
            
            return dict(row)

    def close(self):
        if hasattr(self._local, 'conn') and self._local.conn:
            self._local.conn.close()
            self._local.conn = None

