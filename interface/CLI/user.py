import sys
from time import sleep

from loguru import logger

from util import Config, Data, Info, Login, Request
from util.Info import InfoException
from util.Login import LoginException


class UserCli:
    """
    用户配置交互
    """

    @logger.catch
    def __init__(self, conf: Config):
        """
        初始化

        conf: 配置实例
        """
        self.conf = conf

        self.data = Data()
        self.net = Request()

        # 配置
        self.config = {
            # Cookie
            "cookie": {},
            # Header
            "header": {},
            # 购买人
            "buyer": [],
            # 绑定手机号
            "phone": "",
        }

    @logger.catch
    def Select(self, selects: list) -> dict:
        """
        选择配置

        selects: 可选择项目
        """
        if selects[-1] != "新建用户配置":
            selects.append("新建用户配置")

        select = self.data.Inquire(type="List", message="请选择加载的用户配置", choices=selects)

        if select == "新建用户配置":
            return self.Generate()

        else:
            self.config = self.conf.Load(filename=select, decrypt=True)
            net = Request(cookie=self.config["cookie"], header=self.config["header"])
            Login(net=net).Status()
            return self.config

    @logger.catch
    def Generate(self) -> dict:
        """
        生成配置
        """

        @logger.catch
        def LoginStep() -> dict:
            """
            登录
            """
            login = Login(net=self.net)
            mode = self.data.Inquire(
                type="List",
                message="请选择B站账号登录模式",
                # choices=["扫描二维码", "浏览器登录", "账号密码登录", "手机验证码登录", "手动输入Cookie"],
                choices=["扫描二维码", "浏览器登录", "手动输入Cookie"],
            )

            try:
                match mode:
                    case "扫描二维码":
                        print("请使用B站手机客户端扫描二维码, 如果命令行内二维码无法正常显示, 请打开软件目录下的 qr.jpg 进行扫描")
                        return login.QRCode()

                    case "浏览器登录":
                        return login.Selenium()

                    case "账号密码登录":
                        username = self.data.Inquire(
                            type="Text",
                            message="请输入B站账号",
                        )
                        password = self.data.Inquire(
                            type="Password",
                            message="请输入B站密码",
                        )
                        return login.Password(username=username, password=password)

                    case "手机验证码登录":
                        tel = self.data.Inquire(
                            type="Text",
                            message="请输入手机号",
                        )
                        captcha_key = login.SMSSend(tel)
                        if captcha_key:
                            code = self.data.Inquire(
                                type="Text",
                                message="请输入验证码",
                            )
                            return login.SMSVerify(tel=tel, code=code, captcha_key=captcha_key)
                        else:
                            raise LoginException("验证码发送失败!")

                    case "手动输入Cookie":
                        cookie = self.data.Inquire(
                            type="Text",
                            message="请输入Cookie",
                        )
                        return login.Cookie(cookie=cookie)

                    case _:
                        raise LoginException("未知登录模式, 请重新选择!")

            except LoginException:
                logger.warning("【登录】登录失败, 请重新选择登录模式!")
                return LoginStep()

        @logger.catch
        def BuyerStep() -> list:
            """
            购买人
            """
            try:
                buyerInfo = Info(net=self.net).Buyer()
                choice = {f"{i['购买人']} - {i['身份证']} - {i['手机号']}": x for x, i in enumerate(buyerInfo)}

                select = self.data.Inquire(
                    type="Checkbox",
                    message="请选择购票人, 按空格勾选, 完成后回车, 请确认该活动最多支持几人购票!",
                    choices=list(choice.keys()),
                )

                if len(select) == 0:
                    logger.error("【选择购买人】没人购买是吧?")
                    return BuyerStep()

                dist = []
                for i in select:
                    id = choice[i]
                    dist.append(buyerInfo[id]["数据"])
                return dist

            except InfoException:
                logger.error("选择错误! 请重新打开进行配置")
                sleep(5)
                sys.exit()

        @logger.catch
        def PhoneStep() -> str:
            """
            绑定手机号
            """
            phone = self.data.Inquire(
                type="Text",
                message="请输入你的B站号绑定的手机号, 如果错误有可能无法通过验证码",
            )
            if len(phone) != 11 and len(phone) != 0:
                logger.error("【绑定手机号】手机号格式错误, 请重新输入!")
                return PhoneStep()
            elif len(phone) == 0:
                logger.warning("【绑定手机号】未设置绑定手机号, 可能无法通过验证码!")
            return phone

        @logger.catch
        def FilenameStep(name: str) -> str:
            """
            文件名

            name: 实名名称
            """
            filename = self.data.Inquire(
                type="Text",
                message="保存的用户文件名称",
                default=name[0] + "X" + name[-1],
            )
            return filename

        print("下面开始配置用户!")
        self.config["cookie"] = LoginStep()
        self.config["header"] = self.net.GetHeader()
        self.config["buyer"] = BuyerStep()
        self.config["phone"] = PhoneStep()
        self.conf.Save(FilenameStep(name=self.config["buyer"][0]["name"]), self.config, encrypt=True)
        return self.config
