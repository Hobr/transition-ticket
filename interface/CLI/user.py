from loguru import logger

from util import Config, Data, Info, Login, Request


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
            "buyer": {},
        }

    @logger.catch
    def Select(self, selects: list) -> dict:
        """
        选择配置

        selects: 可选择项目
        """
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
                choices=["扫描二维码", "浏览器登录", "手动输入Cookie", "账号密码登录"]
            )

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
                    try:
                        captcha_key = login.SMSSend(tel)
                        if captcha_key:
                            code = self.data.Inquire(
                                type="Text",
                                message="请输入验证码",
                            )
                            return login.SMSVerify(tel=tel, code=code, captcha_key=captcha_key)
                        else:
                            raise Exception("验证码发送失败!")
                    except Exception as e:
                        logger.exception(f"【登录】登录错误 {e}")
                        return LoginStep()

                case "手动输入Cookie":
                    cookie = self.data.Inquire(
                        type="Text",
                        message="请输入Cookie",
                    )
                    return login.Cookie(cookie=cookie)

                case _:
                    logger.error("【登录】未知登录模式!")
                    exit()

        @logger.catch
        def BuyerStep() -> dict:
            """
            购买人
            """
            buyerInfo = Info(net=self.net).Buyer()
            choice = {f"{i['购买人']} - {i['身份证']} - {i['手机号']}": x for x, i in enumerate(buyerInfo)}

            select = self.data.Inquire(
                type="List",
                message="请选择购票人",
                choices=list(choice.keys()),
            )

            id = choice[select]
            dist = buyerInfo[id]["数据"]
            return dist

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
        self.conf.Save(FilenameStep(name=self.config["buyer"]["name"]), self.config, encrypt=True)
        return self.config
