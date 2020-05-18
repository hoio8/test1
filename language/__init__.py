# encoding: UTF-8

import json
import os

# 默认设置
from .chinese import text, constant

# 获取目录上级路径
path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
SETTING_FILENAME = 'VT_setting.json'
SETTING_FILENAME = os.path.join(path, SETTING_FILENAME)

# 打开配置文件，读取语言配置
try:
    # f = file(SETTING_FILENAME)    # zhb 2020-5-7 python3不再支持file函数，改用open函数
    # print(SETTING_FILENAME)
    f = open(SETTING_FILENAME)  # zhb 2020-5-7 新增
    setting = json.load(f)
    if setting['language'] == 'english':
        from .english import text, constant
    f.close()
except:
    # print('%s can not open'%SETTING_FILENAME) # zhb 2020-5-7 测试增加
    pass
