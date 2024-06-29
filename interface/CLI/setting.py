import re
import time

from loguru import logger

from util import Config, Data


class SettingCli:
    """
    设置配置交互
    """

    # 提醒模式
    noticeMode = ["系统提醒", "音频提醒", "微信提醒(Push Plus)"]

    @logger.catch
    def __init__(self, conf: Config):
        """
        初始化

        conf: 配置实例
        """
        self.conf = conf

        self.data = Data()

        # 配置
        self.config = {
            # 网络
            "request": {
                # 请求间隔
                "sleep": 1.0,
                # 超时
                "timeout": 3.0,
                # 代理
                "proxy": None,
            },
            # 提醒
            "notice": {
                # 系统提醒
                "system": False,
                # 音频提醒
                "sound": False,
                # 微信提醒
                "wechat": False,
                # Plus Push Token
                "plusPush": "",
            },
        }

    @logger.catch
    def Select(self, selects: list) -> dict:
        """
        选择配置

        selects: 可选择项目
        """
        selects.append("新建配置")
        select = self.data.Inquire(type="List", message="请选择加载的设置配置", choices=selects)

        if select == "新建配置":
            return self.Generate()

        else:
            self.config = self.conf.Load(filename=select)
            return self.config

    @logger.catch
    def Generate(self) -> dict:
        """
        生成配置
        """

        @logger.catch
        def SleepStep() -> float:
            """
            请求间隔
            """
            interval = self.data.Inquire(
                type="Text",
                message="请输入创建订单请求间隔时间(单位:秒), 太快会被风控!",
                default="1.0",
            )
            return float(interval)

        @logger.catch
        def TimeoutStep() -> float:
            """
            超时
            """
            timeout = self.data.Inquire(
                type="Text",
                message="请输入请求超时时间(单位:秒)",
                default="3.0",
            )
            return float(timeout)

        @logger.catch
        def ProxyStep() -> str | None:
            """
            代理
            """
            select = self.data.Inquire(
                type="Confirm",
                message="是否使用代理, 默认为否",
                default=False,
            )
            if select:
                proxy = self.data.Inquire(
                    type="Text",
                    message="请输入代理地址",
                    default="http://xxxx.xxx:8080",
                )
                return proxy
            return None

        @logger.catch
        def NoticeStep() -> tuple[bool, bool, bool, str]:
            """
            提醒
            """
            dist = {
                "system": False,
                "sound": False,
                "wechat": False,
                "plusPush": "",
            }
            select = self.data.Inquire(
                type="Checkbox",
                message="抢票成功通知方式",
                choices=[
                    ("系统提醒", "system"),
                    ("音频提醒", "sound"),
                    ("微信提醒(Push Plus)", "wechat"),
                ],
                default=["系统提醒", "音频提醒"],
            )
            for i in select:
                dist[i] = True

            if "wechat" in select:
                token = self.data.Inquire(
                    type="Text",
                    message="请输入Push Plus Token",
                    default="",
                )
                dist["plusPush"] = token

            return dist["system"], dist["sound"], dist["wechat"], dist["plusPush"]

        @logger.catch
        def FilenameStep() -> str:
            """
            文件名
            """
            default = re.sub(r'[\\/*?:"<>|]', "_", time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()))
            filename = self.data.Inquire(
                type="Text",
                message="保存的设置文件名称",
                default=default,
            )
            return filename

        print("下面开始配置设置!")
        self.config["request"]["sleep"] = SleepStep()
        self.config["request"]["timeout"] = TimeoutStep()
        self.config["request"]["proxy"] = ProxyStep()
        (
            self.config["notice"]["system"],
            self.config["notice"]["sound"],
            self.config["notice"]["wechat"],
            self.config["notice"]["plusPush"],
        ) = NoticeStep()

        self.conf.Save(FilenameStep(), self.config)
        logger.info("【设置配置初始化】配置已保存!")
        return self.config
