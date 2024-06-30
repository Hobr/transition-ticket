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

        self.appName = "Bilibili_Show_Python"
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
            base_path = sys._MEIPASS  # type: ignore
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
        )  # type: ignore

    @logger.catch
    def Sound(self, time: int = 2) -> None:
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
