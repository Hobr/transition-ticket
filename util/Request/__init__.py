import logging

import hishel
import httpx
from fake_useragent import UserAgent
from loguru import logger


class Request:
    """
    网络请求
    """

    @logger.catch
    def __init__(
        self,
        cookie: dict = {},
        header: dict = {},
        timeout: float = 5.0,
        retry: int = 3,
        proxy: str | None = None,
        redirect: bool = True,
        isDebug: bool = False,
    ):
        """
        初始化

        cookie: Dict Cookie
        timeout: 超时
        retry: 重试次数
        proxy: 代理
        redirect: 重定向
        isDebug: 调试模式
        """

        self.cookie = cookie
        self.timeout = timeout
        self.retry = retry
        self.proxy = proxy
        self.redirect = redirect
        self.isDebug = isDebug

        self.header = {
            "Accept": "*/*",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Authority": "show.bilibili.com",
            "Connection": "keep-alive",
            "Referer": "https://show.bilibili.com",
            "Origin": "https://show.bilibili.com/",
            "Connection": "keep-alive",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "User-Agent": UserAgent(os="android", platforms="mobile").random,
        } | header

        self.session = hishel.CacheClient(
            cookies=self.cookie,
            headers=self.header,
            timeout=self.timeout,
            proxy=self.proxy,
            # 重定向
            follow_redirects=self.redirect,
            # HTTP2
            http2=True,
            # SSL
            verify=False,
            # Hook
            event_hooks={
                "request": [self.RequestHook],
                "response": [self.ResponseHook],
            },
            # 缓存
            controller=hishel.Controller(
                # 缓存请求模式
                cacheable_methods=["GET", "POST"],
                # 缓存状态码
                cacheable_status_codes=[200],
                # 无法新连接时读取缓存
                allow_stale=False,
                # 强制刷新缓存
                always_revalidate=True,
            ),
        )

        # 关闭Httpx自带日志
        logging.getLogger("httpx").setLevel(logging.CRITICAL)

    @logger.catch
    def Response(self, method: str, url: str, params: dict = {}) -> httpx.Response:
        """
        网络

        method: 方法 post/get
        url: 地址 str
        params: 参数 dict
        """
        methods = {
            "get": self.session.get,
            "post": self.session.post,
        }

        if method not in methods:
            raise

        for _ in range(self.retry):
            try:
                return methods[method](url=url, **({"params": params} if method == "get" else {"data": params}))

            except httpx.RequestError as e:
                logger.exception(f"【网络请求】请求错误: {e}")

        logger.debug("【网络请求】疑似IP被Ban/无网络!")
        quit()

    @logger.catch
    def GetCookie(self) -> dict:
        """
        获取Cookie
        """
        return dict(self.session.cookies)

    @logger.catch
    def GetHeader(self) -> dict:
        """
        获取Header
        """
        return self.header

    @logger.catch
    def RefreshCookie(self, cookie: dict) -> None:
        """
        刷新Cookie

        cookie: Cookie
        """
        self.cookie = cookie
        self.session.cookies.update(self.cookie)

    @logger.catch
    def RequestHook(self, request: httpx.Request) -> None:
        """
        请求事件钩子
        """
        # 调试模式
        if self.isDebug:
            if "show.bilibili.com" in str(request.url):
                logger.debug(f"【Request请求】地址: {request.url} 方法: {request.method} 内容: {request.content} 请求参数: {request.read()}")
            else:
                logger.debug(f"【Request请求】地址: {request.url} 方法: {request.method}")

    @logger.catch
    def ResponseHook(self, response: httpx.Response) -> None:
        """
        响应事件钩子
        """
        request = response.request
        # 调试模式
        if self.isDebug:
            if "show.bilibili.com" in str(request.url):
                logger.debug(f"【Request响应】地址: {request.url} 状态码: {response.status_code} 返回: {response.read()}")
            else:
                logger.debug(f"【Request响应】地址: {request.url} 状态码: {response.status_code}")

        # 风控
        if response.status_code != 200:
            if response.status_code != 412:
                if "show.bilibili.com" in str(request.url):
                    logger.error(f"【Request响应】请求错误, 状态码: {response.status_code}")
            else:
                logger.error("【Request响应】IP被412风控!!!!! 请更换IP(重启路由器/使用手机流量热点/梯子......)后再次使用")
                exit()
