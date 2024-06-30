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
                # 开票黄金时间
                "gold": 35.0,
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
            # 开发者
            "dev": {
                # 开发者模式
                "debug": False,
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
        def GoldStep() -> float:
            """
            开票黄金时间
            """
            time = self.data.Inquire(
                type="Text",
                message="请输入开票黄金时间(单位:分钟), 在开票后的相应时间内会无视无票提示",
                default="35.0",
            )
            return float(time)

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
                message="抢票成功通知方式, 按空格勾选",
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
        self.config["request"]["gold"] = GoldStep()
        (
            self.config["notice"]["system"],
            self.config["notice"]["sound"],
            self.config["notice"]["wechat"],
            self.config["notice"]["plusPush"],
        ) = NoticeStep()

        self.conf.Save(FilenameStep(), self.config)
        logger.info("【设置配置初始化】配置已保存!")
        return self.config
