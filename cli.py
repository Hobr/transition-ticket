import atexit
import shutil
import sys

from loguru import logger

from interface import ProductCli, SettingCli, UserCli
from util import Bilibili, Captcha, Config, Request, Task


def cleanup_meipass() -> None:
    if hasattr(sys, "_MEIPASS"):
        meipass_path = sys._MEIPASS
        try:
            shutil.rmtree(meipass_path)
            print(f"正在清理 {meipass_path}")
        except Exception as e:
            print(f"清理失败 {meipass_path}: {e}")


atexit.register(cleanup_meipass)

if __name__ == "__main__":
    # 丢锅
    print(
        """
|=====================================================================
|
|  欢迎使用 github.com/biliticket/transition-ticket
|  TG交流群 t.me/bilibili_ticket
|  本程序仅供学习交流, 不得用于商业用途
|  使用本程序进行违法操作产生的法律责任由操作者自行承担
|  对本程序进行二次开发/分发时请注意遵守GPL-3.0开源协议
|  本脚本仅适用于蹲回流票, 我们反对将其用于抢票
|  黄牛 / 收费代抢 ４０００＋
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
        colorize=False,
        enqueue=True,
        encoding="utf-8",
        # 调试
        backtrace=True,
        diagnose=True,
    )

    # 验证
    cap = Captcha()
    settingData = Config(dir="setting")
    userData = Config(dir="user")
    productData = Config(dir="product")

    while True:
        # 读取配置
        settingList = settingData.List()
        settingConfig = SettingCli(conf=settingData).Select(selects=settingList) if settingList != [] else SettingCli(conf=settingData).Generate()

        userList = userData.List()
        userConfig = (
            UserCli(conf=userData, isEncrypt=settingConfig["dev"]["isEncrypt"]).Select(selects=userList)
            if userList != []
            else UserCli(conf=userData, isEncrypt=settingConfig["dev"]["isEncrypt"]).Generate()
        )

        productList = productData.List()
        productConfig = ProductCli(conf=productData).Select(selects=productList) if productList != [] else ProductCli(conf=productData).Generate()

        net = Request(
            cookie=userConfig["cookie"],
            header=userConfig["header"],
            timeout=settingConfig["request"]["timeout"],
            proxy=settingConfig["request"]["proxy"],
            isDebug=settingConfig["dev"]["debug"],
            rest=settingConfig["request"]["rest"],
        )

        api = Bilibili(
            net=net,
            projectId=productConfig["projectId"],
            screenId=productConfig["screenId"],
            skuId=productConfig["skuId"],
            buyer=userConfig["buyer"],
            count=len(userConfig["buyer"]),
            deliver=userConfig["deliver"],
            phone=userConfig["phone"],
            userinfo=userConfig["userinfo"],
        )

        job = Task(
            net=net,
            cap=cap,
            api=api,
            notice=settingConfig["notice"],
            sleep=settingConfig["request"]["sleep"],
            isDebug=settingConfig["dev"]["debug"],
        )

        # 任务流
        if not job.Run():
            break
