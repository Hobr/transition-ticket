from loguru import logger

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
        self.appName = "Bilibili_Show_Python"
        self.appIconPath = "./assest/icon.ico"
        self.audioPath = "./assest/alarm.wav"

        self.title = title
        self.message = message

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
        )  # type: ignore

    @logger.catch
    def Sound(self, time: int = 2) -> None:
        """
        声音
        """
        import pyaudio

        p = pyaudio.PyAudio()
        stream = p.open(format=pyaudio.paInt16, channels=1, rate=44100, output=True)

        for _ in range(time):
            stream.write(open(self.audioPath, "rb").read())

        stream.stop_stream()
        stream.close()

    @logger.catch
    def PushPlus(self, token: str) -> None:
        """
        PushPlus

        文档: https://pushplus.plus/doc/

        link: 需要用户点击跳转的链接
        """
        url = "http://www.pushplus.plus/send"
        data = {
            "token": token,
            "title": self.title,
            "content": self.message,
            "template": "html",
            "channel": "wechat",
        }
        Request().Response(method="post", url=url, params=data)
