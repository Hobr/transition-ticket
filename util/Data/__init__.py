import base64
import datetime
import json
import os
import sys
from sys import argv
from time import sleep

import inquirer
import machineid
import psutil
import pytz
import qrcode
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from inquirer.themes import GreenPassion
from loguru import logger


class CustomThemes(GreenPassion):
    def __init__(self):
        super().__init__()
        self.List.selection_cursor = "->"  # 选择光标 # type: ignore
        self.List.selection_color = "\033[1;35;106m"  # 设置 List选项 的选中颜色(紫，蓝) # type: ignore
        self.Question.mark_color = "\033[93m"  # 设置 [?] 中 ? 的颜色(黄) # type: ignore
        self.Question.brackets_color = "\033[96m"  # 设置 [?] 中 [] 的颜色(蓝) # type: ignore


class Data:
    """
    数据处理
    """

    @logger.catch
    def JsonpToDict(self, data: str) -> dict:
        """
        JSONP转JSON

        data: 待转换数据
        """
        startIndex = data.find("(") + 1
        endIndex = data.rfind(")")
        json_str = data[startIndex:endIndex]
        return json.loads(json_str)

    @logger.catch
    def QRGenerate(self, url: str) -> None:
        """
        生成二维码

        url: 链接
        img_path: 保存路径
        """
        qr = qrcode.QRCode()  # type: ignore
        qr.add_data(url)
        img = qr.make_image()

        try:
            parent_pid = psutil.Process(os.getpid()).ppid()
            parent_process = psutil.Process(parent_pid)
            parent_name = parent_process.name()
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            logger.error("获取父进程信息失败!")

        if os.name == "nt":
            if parent_name == "powershell.exe" or "WT_SESSION" in os.environ:
                qr.print_ascii(invert=True)
            elif parent_name == "cmd.exe" or argv[0].endswith(".exe"):
                img.show()
            else:
                qr.print_ascii(invert=True)
        else:
            qr.print_ascii(invert=True)

    @logger.catch
    def SeleniumCookieFormat(self, cookie: list) -> dict:
        """
        将Selenium输出的Cookie转为标准Cookie

        cookie: Selenium输出的Cookie
        """
        dist = {}
        for i in cookie:
            dist[i["name"]] = i["value"]
        return dist

    @logger.catch
    def StrCookieFormat(self, cookie: str) -> dict:
        """
        将字符串Cookie转为标准Cookie

        cookie: 字符串Cookie
        """
        dist = {}
        cookies = cookie.split("; ")
        for i in cookies:
            if "=" in i:
                key, value = i.split("=", 1)
                dist[key] = value
        return dist

    @logger.catch
    def TimestampFormat(
        self,
        timestamp: int,
        format_type: str = "s",
        countdown: bool = False,
    ) -> str:
        """
        时间戳转换

        timestamp: 时间戳
        format_type: 精确到 s: 秒 m: 分 d: 天
        countdown: 是否为 倒计时时间戳
        """
        if countdown:
            if timestamp > 0:
                countdown_delta = datetime.timedelta(seconds=timestamp)
                days = countdown_delta.days
                hours, remainder = divmod(countdown_delta.seconds, 3600)
                minutes, seconds = divmod(remainder, 60)
                return f"{days}天{hours}时{minutes}分{seconds}秒"
            else:
                return ""

        else:
            CST = pytz.timezone("Asia/Shanghai")
            formatted_time = datetime.datetime.fromtimestamp(timestamp, tz=CST)
            match format_type:
                case "s":
                    return formatted_time.strftime("%Y-%m-%d %H:%M:%S")
                case "m":
                    return formatted_time.strftime("%Y-%m-%d %H:%M")
                case "d":
                    return formatted_time.strftime("%Y-%m-%d")
                case _:
                    logger.exception("【时间戳转换】时间错误")
                    return ""

    @logger.catch
    def TimestampCheck(self, timestamp: int, duration: int = 15) -> bool:
        """
        时间戳有效性检查

        timestamp: 开始时间戳
        duration: 持续时间 分钟
        """
        timestamp_now = datetime.datetime.now().timestamp()
        return timestamp + duration * 60 >= timestamp_now >= timestamp

    @logger.catch
    def PasswordRSAEncrypt(self, password: str, public_key: str) -> str:
        """
        RSA加密密码

        password: 密码
        public_key: 公钥
        """
        from Crypto.Cipher import PKCS1_v1_5
        from Crypto.PublicKey import RSA

        key = RSA.import_key(public_key)
        cipher = PKCS1_v1_5.new(key)
        cipher_text = cipher.encrypt(password.encode())

        return base64.b64encode(cipher_text).decode("utf-8")

    @logger.catch
    def AESEncrypt(self, data: str) -> str:
        """
        AES-128 加密

        data: 数据
        key: 硬件ID
        """
        key = machineid.id().encode()[:16]
        cipher = AES.new(key, AES.MODE_ECB)
        cipher_text = cipher.encrypt(pad(data.encode(), AES.block_size))
        return base64.b64encode(cipher_text).decode("utf-8")

    @logger.catch
    def AESDecrypt(self, data: str) -> str:
        """
        AES-128 解密

        data: 数据
        key: 硬件ID
        """
        key = machineid.id().encode()[:16]
        cipher = AES.new(key, AES.MODE_ECB)
        cipher_text = base64.b64decode(data.encode("utf-8"))
        try:
            decrypted_text = unpad(cipher.decrypt(cipher_text), AES.block_size)
            return decrypted_text.decode("utf-8")
        except Exception:
            logger.error("【解密】这是你的配置吗?")
            logger.warning("程序正在准备退出...")
            sleep(5)
            sys.exit()

    @logger.catch
    def CookieAppend(self, baseCookie: dict) -> dict:
        """
        补充非浏览器登录用户Cookie数据

        baseCookie: 基础Cookie
        """
        # 已知
        dist = {
            # https://blog.csdn.net/weixin_41489908/article/details/130643493
            "_uuid": "",
            # https://blog.csdn.net/weixin_41489908/article/details/130686625
            "b_lsid": "",
            # https://github.com/SocialSisterYi/bilibili-API-collect/issues/795#issuecomment-1805005704
            "b_nut": "",
            # https://github.com/SocialSisterYi/bilibili-API-collect/blob/master/docs/misc/sign/bili_ticket.md
            "bili_ticket": "",
            "bili_ticket_expires": "",
            # https://api.bilibili.com/x/frontend/finger/spi
            "buvid4": "",
            # https://github.com/SocialSisterYi/bilibili-API-collect/issues/933#issuecomment-1931506993
            "fingerprint": "",
            # TODO 浏览器JS
            "deviceFingerprint": "",
        }
        dist["buvid_fp"] = dist["fingerprint"]
        return dist | baseCookie

    @logger.catch
    def Inquire(
        self,
        type: str = "Text",
        message: str = "",
        choices: list | None = None,
        default: str | list | bool | None = None,
    ) -> str:
        """
        交互

        type: 交互类型 Text, Confirm, List, Checkbox
        message: 提示信息
        default: 默认值 根据type决定类型
        choices: 选项
        """
        choiceMethod = ["List", "Checkbox"]
        method = {
            "Text": inquirer.Text,
            "Confirm": inquirer.Confirm,
            "List": inquirer.List,
            "Checkbox": inquirer.Checkbox,
            "Password": inquirer.Password,
        }

        process = method[type]
        res = inquirer.prompt(
            [
                process(
                    name="res",
                    message=message,
                    default=default,
                    **({"choices": choices} if type in choiceMethod else {}),
                )
            ],
            theme=CustomThemes(),
        )

        if res is not None:
            return res["res"]
        else:
            logger.error("【交互】未知错误!")
            logger.warning("程序正在准备退出...")
            sleep(5)
            sys.exit()
