import sys
from os import getcwd, path

from loguru import logger

from util.Login import Login
from util.Request import Request


class Notice:
    """
    提示
    """

    @logger.catch
    def __init__(
        self,
        title: str,
        message: str,
    ) -> None:
        """
        初始化

        title: 标题
        message: 消息
        """
        self.net = Request()
        self.login = Login(net=self.net)

        self.appName = "Transition-Ticket"
        self.appIconPath = self.AssestDir("assest/icon.ico")
        self.audioPath = self.AssestDir("assest/alarm.wav")

        self.title = title
        self.message = message

    @logger.catch
    def AssestDir(self, dir: str):
        """
        获取资源文件夹(涉及到Pyinstaller)
        """
        try:
            base_path = sys._MEIPASS
        except AttributeError:
            base_path = getcwd()
        return path.join(base_path, dir)

    @logger.catch
    def Message(self, timeout: int = 10) -> None:
        """
        弹窗
        """
        from plyer import notification

        notification.notify(
            title=self.title,
            message=self.message,
            app_icon=self.appIconPath,
            app_name=self.appName,
            timeout=timeout,
        )

    @logger.catch
    def Sound(self, time: int = 3) -> None:
        """
        声音
        """
        import pyaudio

        p = pyaudio.PyAudio()
        stream = p.open(format=pyaudio.paInt16, channels=1, rate=44100, output=True)

        with open(self.audioPath, "rb") as audio_file:
            audio_data = audio_file.read()
            for _ in range(time):
                stream.write(audio_data)

        stream.stop_stream()
        stream.close()

    @logger.catch
    def PushPlus(self, token: str) -> None:
        """
        PushPlus

        文档: https://pushplus.plus/doc/
        """
        url = "http://www.pushplus.plus/send"
        data = {
            "token": token,
            "title": self.title,
            "content": self.message,
            "template": "html",
            "channel": "wechat",
        }

        self.net.Response(method="post", url=url, params=data, isJson=False)

    @logger.catch
    def Ding(self, token: str) -> None:
        """
        钉钉
        """
        url = f"https://oapi.dingtalk.com/robot/send?access_token={token}"
        data = {"msgtype": "text", "text": {"content": self.message}, "at": {"isAtAll": False}}
        self.net.Response(method="post", url=url, params=data)

    @logger.catch
    def WX(self, token: str) -> None:
        """
        微信
        """
        url = f"https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key={token}"
        data = {"msgtype": "text", "text": {"content": self.message}}
        self.net.Response(method="post", url=url, params=data)

    @logger.catch
    def FTQQ(self, token: str) -> None:
        """
        方糖
        """
        url = f"https://sctapi.ftqq.com/{token}.send"
        data = {"title": self.title, "desp": self.message, "noip": 1}
        self.net.Response(method="post", url=url, params=data)

    @logger.catch
    def Bark(self, token: str) -> None:
        """
        Bark
        """
        url = f"https://api.day.app/{token}"
        data = {
            "title": self.title,
            "body": self.message,
            "level": "timeSensitive",
            # 推送中断级别。
            # active：默认值，系统会立即亮屏显示通知
            # timeSensitive：时效性通知，可在专注状态下显示通知。
            # passive：仅将通知添加到通知列表，不会亮屏提醒。"""
            "badge": 1,
            "icon": "https://ys.mihoyo.com/main/favicon.ico",
            "group": "BHYG",
            "isArchive": 1,
        }
        self.net.Response(method="post", url=url, params=data)

    @logger.catch
    def Mail(self, params: dict) -> None:
        """
        SMTP
        """
        import smtplib
        from email.mime.text import MIMEText

        # 设置服务器所需信息
        # 163邮箱服务器地址
        mail_host = params["mail_host"]
        # 163用户名
        mail_user = params["mail_user"]
        # 密码(部分邮箱为授权码)
        mail_pass = params["mail_pass"]
        # 邮件发送方邮箱地址
        sender = params["sender"]
        # 邮件接受方邮箱地址，注意需要[]包裹，这意味`着你可以写多个邮件地址群发
        receivers = params["receiver"]

        # 设置email信息
        # 邮件内容设置
        message = MIMEText(self.message, "plain", "utf-8")
        # 邮件主题
        message["Subject"] = self.title
        # 发送方信息
        message["From"] = sender
        # 接受方信息
        for receiver in receivers:
            message["To"] = receiver

            # 登录并发送邮件
            try:
                smtpObj = smtplib.SMTP()
                # 连接到服务器
                smtpObj.connect(mail_host, 25)
                # 登录到服务器
                smtpObj.login(mail_user, mail_pass)
                # 发送
                smtpObj.sendmail(sender, receivers, message.as_string())
                # 退出
                smtpObj.quit()
                # logger.info(i18n_format("send_success"))
                logger.info("邮件提醒发送成功")
            except smtplib.SMTPException as e:
                logger.error(e)  # 打印错误
