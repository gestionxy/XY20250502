# System/fonts/fonts.py
import os
from matplotlib import font_manager

def load_chinese_font():
    font_path = os.path.join("System", "fonts", "SimHei.ttf")  # 确保路径和文件名正确
    if not os.path.exists(font_path):
        print("[错误] 中文字体文件未找到:", font_path)
        return None
    return font_manager.FontProperties(fname=font_path)

