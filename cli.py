import os
import shutil
import threading

from bili_ticket_gt_python import ClickPy
from loguru import logger

from interface import ProductCli, SettingCli, UserCli
from util import Captcha, Config, Notice, Request, Task

if __name__ == "__main__":
    # 丢锅
    print(
        """
|=====================================================================
|
|  欢迎使用https://github.com/bilibili-ticket/bilibili-ticket-python
|  本程序仅供学习交流, 不得用于商业用途
|  使用本程序进行违法操作产生的法律责任由操作者自行承担
|  对本程序进行二次开发/分发时请注意遵守GPL-3.0开源协议
|  本脚本仅适用于蹲回流票, 我们反对将其用于抢票
|
|=====================================================================
|
|  交互: 上下 键盘↑↓键, 多选 空格, 确认 回车
|
|=====================================================================
"""
    )

    # 日志
    logger.add(
        "log/{time}.log",
        colorize=True,
        enqueue=True,
        encoding="utf-8",
        # 日志保留天数
        retention=3,
        # 调试
        backtrace=True,
        diagnose=True,
    )

    # 删除缓存
    if os.path.exists(".cache"):
        shutil.rmtree(".cache")

    # 初始化
    # 用户数据文件
    userData = Config(dir="user")
    productData = Config(dir="product")
    settingData = Config(dir="setting")
    # 验证
    verify = ClickPy()
    cap = Captcha(verify=verify)

    # 检测配置文件情况
    userList = userData.List()
    productList = productData.List()
    settingList = settingData.List()

    # 读取配置
    if userList != []:
        userConfig = UserCli(conf=userData).Select(selects=userList)
    else:
        userConfig = UserCli(conf=userData).Generate()

    if productList != []:
        productConfig = ProductCli(conf=productData).Select(selects=productList)
    else:
        productConfig = ProductCli(conf=productData).Generate()

    if settingList != []:
        settingConfig = SettingCli(conf=settingData).Select(selects=settingList)
    else:
        settingConfig = SettingCli(conf=settingData).Generate()

    net = Request(
        cookie=userConfig["cookie"],
        header=userConfig["header"],
        timeout=settingConfig["request"]["timeout"],
        retry=settingConfig["request"]["retry"],
        proxy=settingConfig["request"]["proxy"],
    )

    job = Task(
        net=net,
        cap=cap,
        sleep=settingConfig["request"]["sleep"],
        projectId=productConfig["projectId"],
        screenId=productConfig["screenId"],
        skuId=productConfig["skuId"],
        buyer=userConfig["buyer"],
    )

    # job.DrawFSM()

    # 任务流
    if job.Run():
        notice = Notice(title="抢票", message="下单成功! 请在十分钟内支付")
        mode = settingConfig["notice"]
        logger.info("【抢票】下单成功! 请在十分钟内支付")

        # 多线程通知
        noticeThread = []
        t1 = threading.Thread(target=notice.Message)
        t2 = threading.Thread(target=notice.Sound)
        t3 = threading.Thread(target=notice.PushPlus, args=(mode["plusPush"],))

        if mode["system"]:
            noticeThread.append(t1)
        if mode["sound"]:
            noticeThread.append(t2)
        if mode["wechat"]:
            noticeThread.append(t3)

        for t in noticeThread:
            t.start()
