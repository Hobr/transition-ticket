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
                "sleep": 0.8,
                # 412风控间隔
                "rest": 60.0,
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
                # push plus token
                "pushplus_token": "",
                # 钉钉推送token
                "dingding_token": "",
                # 企业微信推送token
                "wx_token": "",
                # 企业微信推送token
                "ftqq_token": "",
                # bark推送token
                "bark_token": "",
                # smtp邮件推送
                "smtp_mail_host": "",
                "smtp_mail_user":"",
                "smtp_mail_pass":"",
                "smtp_sender":"",
                "smtp_receiver":"",
               
            
            
            },
            # 开发者
            "dev": {
                # 加密用户数据
                "isEncrypt": True,
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
        if selects[-1] != "新建系统配置":
            selects.append("新建系统配置")

        select = self.data.Inquire(type="List", message="请选择加载的系统配置", choices=selects)

        if select == "新建系统配置":
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
                message="请输入创建订单请求间隔时间(单位:秒), 太快有概率会被风控!",
                default="0.8",
            )
            return float(interval)

        @logger.catch
        def RestStep() -> float:
            """
            412风控间隔
            """
            rest = self.data.Inquire(
                type="Text",
                message="请输入触发412风控时暂停的时间(单位:秒), 建议高于默认值!",
                default="60",
            )
            return float(rest)

        @logger.catch
        def NoticeStep() -> tuple[bool, bool, bool, str]:
            """
            提醒
            """
            dist = {
                "system": False,
                "sound": False,
                "wechat": False,
                "dingding_token": "",
                "ftqq_token": "",
                "bark_token": "",
                "wx_token": "",
                "smtp_mail_host": "",
                "smtp_mail_user":"",
                "smtp_mail_pass":"",
                "smtp_sender":"",
                "smtp_receiver":"",
                "pushplus_token": "",
            }
            select = self.data.Inquire(
                type="Checkbox",
                message="抢票成功通知方式, 按空格勾选",
                choices=[
                    ("系统提醒", "system"),
                    ("音频提醒", "sound"),
                    ("微信提醒(Push Plus)", "pushplus"),
                    ("bark推送","bark"),
                    ("钉钉推送", "dingding"),
                    ("企业微信推送", "wx"),
                    ("smtp邮件推送","smtp"),
                    ("方糖推送","ftqq")
                    
                ],
                default=["系统提醒", "音频提醒"],
            )
            for i in select:
                dist[i] = True

            if "pushplus" in select:
                token = self.data.Inquire(
                    type="Text",
                    message="请输入Push Plus Token",
                    default="",
                )
                dist["pushplus_token"] = token
            
            if "bark" in select:
                token = self.data.Inquire(
                    type="Text",
                    message="请输入bark推送的token",
                    default="",
                )
                dist["bark_token"] = token
            
            if "dingding" in select:
                token = self.data.Inquire(
                    type="Text",
                    message="请输入钉钉推送的token",
                    default="",
                )
                dist["dingding_token"] = token
                
            if "wx" in select:
                token = self.data.Inquire(
                    type="Text",
                    message="请输入企业微信推送的token",
                    default="",
                )
                dist["wx_token"] = token
                
            if "ftqq" in select:
                token = self.data.Inquire(
                    type="Text",
                    message="请输入方糖推送的token",
                    default="",
                )
                dist["ftqq_token"] = token
            
            if "smtp" in select:
                host = self.data.Inquire(
                    type="Text",
                    message="请输入smtp服务器地址",
                    default="",
                )
                user=self.data.Inquire(
                    type='Text',
                    message="请输入用户名",
                    default="",
                 )
                passwd=self.data.Inquire(
                    type='Text',
                    message="请输入密码",
                    default="",
                )
                smtp_sender=self.data.Inquire(
                    type='Text',
                    message="请输入发件人邮箱",
                    default="",
                )
                smtp_receivers=self.data.Inquire(
                    type='Text',
                    message="请输入收件人邮箱,可群发，按照['123456@123.com','123456@123.com']格式输入",
                    default="",
                )
                dist['smtp_mail_host']=host
                dist['smtp_mail_user']=user
                dist['smtp_mail_pass']=passwd
                dist['smtp_sender']=smtp_sender
                dist['smtp_receivers']=smtp_receivers
                

            return dist["system"], dist["sound"], dist["wechat"], dist["pushplus_token"],dist['bark_token'],dist['dingding_token'],dist['ftqq_token'],dist['wx_token'],dist['smtp_mail_host'],dist['smtp_mail_pass'],dist['smtp_mail_user'],dist['smtp_receivers']

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
        self.config["request"]["rest"] = RestStep()
        (
            self.config["notice"]["system"],
            self.config["notice"]["sound"],
            self.config["notice"]["wechat"],
            self.config["notice"]["plusPush"],
        ) = NoticeStep()

        self.conf.Save(FilenameStep(), self.config)
        logger.info("【设置配置初始化】配置已保存!")
        return self.config
