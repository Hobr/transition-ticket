import json
import re
import sys
import time
from time import sleep

import browsers
from loguru import logger
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from util import Captcha, Data, Request


class LoginException(Exception):
    """
    登录异常
    """

    def __init__(self, message):
        self.message = message
        logger.error(f"【登录】{message}")


class Login:
    """
    账号登录

    文档: https://github.com/SocialSisterYi/bilibili-API-collect/blob/master/docs/login/login_action
    """

    @logger.catch
    def __init__(
        self,
        net: Request,
        checkStatus: bool = True,
    ):
        """
        初始化

        net: 网络实例
        isCheckStatus: 是否检查登录状态
        """
        self.net = net
        self.isCheckStatus = checkStatus

        self.cookie = {}
        self.data = Data()
        self.cap = Captcha()

        self.source = "main_web"

    def QRCode(self) -> dict:
        """
        扫码登录

        文档: https://github.com/SocialSisterYi/bilibili-API-collect/blob/master/docs/login/login_action/QR.md
        """
        self.net.Response(method="get", url="https://www.bilibili.com/", isJson=False)

        resp = self.net.Response(
            method="get",
            url="https://passport.bilibili.com/x/passport-login/web/qrcode/generate",
        )

        if resp["code"] == 0:
            url = resp["data"]["url"]
            self.data.QRGenerate(url)

            t = 0
            while True:
                time.sleep(0.5)
                respQR = self.net.Response(
                    method="get",
                    url="https://passport.bilibili.com/x/passport-login/web/qrcode/poll?source=main-fe-header&qrcode_key=" + resp["data"]["qrcode_key"],
                )

                check = respQR["data"]
                if check["code"] == 0:
                    logger.success("【登录】登录成功")
                    self.cookie = self.net.GetCookie()
                    # 补充Cookie参数
                    # self.cookie = Data().CookieAppend(self.cookie) | self.cookie
                    return self.Status()

                # 未扫描:86101 扫描未确认:86090
                elif check["code"] in [86101, 86090]:
                    t += 1
                    if t % 5 == 0:
                        logger.info("【登录】等待扫码...")

                else:
                    raise LoginException(f"{check['code']}: {check['message']}")

        else:
            raise LoginException(f"服务器不知道送来啥东西{json.dumps(resp, indent=4)}")

    def Selenium(self) -> dict:
        """
        Selenium登录

        Chrome WebDriver: https://googlechromelabs.github.io/chrome-for-testing/#stable
        """
        browser_list = [i for i in list(browsers.browsers()) if i["browser_type"] != "msie"]

        if not browser_list:
            raise LoginException("未找到可用浏览器/WebDriver!建议选择其他方式登录")

        selenium_drivers = {
            "chrome": webdriver.Chrome,
            "firefox": webdriver.Firefox,
            "msedge": webdriver.Edge,
            "safari": webdriver.Safari,
        }

        for browser in browser_list:
            browser_type = browser["browser_type"]
            print(f"请在打开的 {browser_type} 浏览器中进行登录")
            driver = selenium_drivers[browser_type]()

            if not driver:
                raise LoginException("所有浏览器/WebDriver尝试登录均失败")

            driver.maximize_window()
            try:
                driver.get("https://show.bilibili.com/")
                wait = WebDriverWait(driver, 30)
                event = wait.until(EC.element_to_be_clickable((By.CLASS_NAME, "nav-header-register")))
                driver.execute_script("arguments[0].click();", event)
                break

            except Exception:
                logger.warning("程序正在准备退出...")
                sleep(5)
                sys.exit()

        while True:
            time.sleep(0.5)
            if driver.page_source is None or "登录" not in driver.page_source:
                break

        logger.success("【登录】登录成功")
        driver.get("https://account.bilibili.com/account/home")
        seleniumCookie = driver.get_cookies()
        logger.info("【登录】Cookie已保存")
        self.cookie = self.data.SeleniumCookieFormat(seleniumCookie)
        driver.quit()
        return self.Status()

    @logger.catch
    def GetCaptcha(self) -> tuple:
        """
        获取Captcha验证码并通过Geetest验证

        文档: https://github.com/SocialSisterYi/bilibili-API-collect/blob/master/docs/login/login_action/readme.md
        """
        resp = self.net.Response(
            method="get",
            url="https://passport.bilibili.com/x/passport-login/captcha?source=main_web",
        )

        if resp["code"] == 0:
            token = resp["data"]["token"]
            challenge = resp["data"]["geetest"]["challenge"]
            validate = self.cap.Geetest(challenge)
            seccode = validate + "|jordan"
            return token, challenge, validate, seccode
        else:
            logger.warning("程序正在准备退出...")
            sleep(5)
            sys.exit()

    @logger.catch
    def GetPreCaptcha(self) -> tuple:
        """
        获取PreCaptcha验证码并通过Geetest验证

        文档: https://github.com/SocialSisterYi/bilibili-API-collect/blob/master/docs/login/login_action/readme.md
        """
        resp = self.net.Response(
            method="post",
            url="https://passport.bilibili.com/x/safecenter/captcha/pre",
        )

        if resp["code"] == 0:
            token = resp["data"]["recaptcha_token"]
            challenge = resp["data"]["gee_challenge"]
            validate = self.cap.Geetest(challenge)
            seccode = validate + "|jordan"
            return token, challenge, validate, seccode
        else:
            logger.warning("程序正在准备退出...")
            sleep(5)
            sys.exit()

    def Password(self, username: str, password: str) -> dict:
        """
        账号密码登录

        username: 用户名
        password: 密码

        文档: https://github.com/SocialSisterYi/bilibili-API-collect/blob/master/docs/login/login_action/password.md
        """
        token, challenge, validate, seccode = self.GetCaptcha()

        salt = self.net.Response(
            method="get",
            url="https://passport.bilibili.com/x/passport-login/web/key",
        )

        salt_hash = salt["data"]["hash"]
        salt_key = salt["data"]["key"]

        params = {
            "username": username,
            "password": self.data.PasswordRSAEncrypt(salt_hash + password, salt_key),
            "keep": "0",
            "token": token,
            "challenge": challenge,
            "validate": validate,
            "seccode": seccode,
            "source": self.source,
        }

        resp = self.net.Response(
            method="post",
            url="https://passport.bilibili.com/x/passport-login/web/login",
            params=params,
        )

        if resp["code"] != 0:
            raise LoginException(f"登录失败 {resp['code']}: {resp['message']}")

        if resp["data"]["status"] == 0:
            logger.success("【登录】登录成功")
            self.cookie = self.net.GetCookie()
            return self.Status()

        else:  # 二次短信验证登录
            logger.warning("【登录】登录失败, 需要二次验证")

            resp_url = resp["data"]["url"]
            tmp_token_match = re.search(r"tmp_token=(\w{32})", resp_url)
            tmp_token = tmp_token_match.group(1) if tmp_token_match else ""
            scene_match = re.search(r"scene=([^&]+)", resp_url)
            scene = scene_match.group(1) if scene_match else "loginTelCheck"

            info = self.net.Response(
                method="get",
                url=f"https://passport.bilibili.com/x/safecenter/user/info?tmp_code={tmp_token}",
            )

            if not info["data"]["account_info"]["bind_tel"]:
                raise LoginException("手机号未绑定, 请重新选择登录方式")

            hide_tel = info["data"]["account_info"]["hide_tel"]
            logger.info(f"【登录】手机号已绑定, 即将给 {hide_tel} 发送验证码")

            token, challenge, validate, seccode = self.GetPreCaptcha()

            resend_params = {
                "tmp_code": tmp_token,
                "sms_type": scene,
                "recaptcha_token": token,
                "gee_challenge": challenge,
                "gee_validate": validate,
                "gee_seccode": seccode,
            }

            resend = self.net.Response(
                method="post",
                url="https://passport.bilibili.com/x/safecenter/common/sms/send",
                params=resend_params,
            )

            if resend["code"] != 0:
                raise LoginException(f"验证码发送失败: {resend['code']} {resend['message']}")

            logger.success("【登录】验证码发送成功")
            resend_token = resend["data"]["captcha_key"]
            verify_code = self.data.Inquire(type="Text", message="请输入验证码")

            if resp["data"]["status"] == 1:
                data = {
                    "verify_type": "sms",
                    "tmp_code": tmp_token,
                    "captcha_key": resend_token,
                    "code": verify_code,
                }
                url = "https://passport.bilibili.com/x/safecenter/sec/verify"

            elif resp["data"]["status"] == 2:
                data = {
                    "type": "loginTelCheck",
                    "tmp_code": tmp_token,
                    "captcha_key": resend_token,
                    "code": verify_code,
                }
                url = "https://passport.bilibili.com/x/safecenter/login/tel/verify"

            else:
                raise LoginException(f"未知错误: {resp['data']['status']}")

            reverify = self.net.Response(method="post", url=url, params=data)

            if reverify["code"] != 0:
                raise LoginException(f"验证码登录失败 {reverify['code']}: {reverify['message']}")

            logger.success("【登录】验证码登录成功")
            self.net.Response(
                method="post",
                url="https://passport.bilibili.com/x/passport-login/web/exchange_cookie",
                params={"source": "risk", "code": reverify["data"]["code"]},
            )
            self.cookie = self.net.GetCookie()
            return self.Status()

    def SMSSend(self, tel: str) -> str:
        """
        手机号登录 - 发送验证码

        tel: 手机号
        返回: captcha_key

        文档: https://github.com/SocialSisterYi/bilibili-API-collect/blob/master/docs/login/login_action/SMS.md
        """
        token, challenge, validate, seccode = self.GetCaptcha()

        params = {
            "cid": "86",
            "tel": tel,
            "source": self.source,
            "token": token,
            "challenge": challenge,
            "validate": validate,
            "seccode": seccode,
        }

        resp = self.net.Response(
            method="post",
            url="https://passport.bilibili.com/x/passport-login/web/sms/send",
            params=params,
        )

        if resp["code"] == 0:
            logger.success("【登录】验证码发送成功")
            captcha_key = resp["data"]["captcha_key"]
            return captcha_key
        else:
            raise LoginException(f"验证码发送失败 {resp['code']}: {resp['message']}")

    def SMSVerify(self, tel: str, code: str, captcha_key: str) -> dict:
        """
        手机号登录 - 发送验证码

        tel: 手机号
        int: 验证码
        captcha_key: 验证token

        文档: https://github.com/SocialSisterYi/bilibili-API-collect/blob/master/docs/login/login_action/SMS.md
        """
        params = {
            "cid": "86",
            "tel": tel,
            "code": code,
            "source": self.source,
            "captcha_key": captcha_key,
            "keep": False,
        }

        resp = self.net.Response(
            method="post",
            url="https://passport.bilibili.com/x/passport-login/web/login/sms",
            params=params,
        )

        if resp["code"] == 0:
            logger.success("【登录】登录成功")
        else:
            raise LoginException(f"验证码登录失败 {resp['code']}: {resp['message']}")

        self.cookie = self.net.GetCookie()
        return self.Status()

    def Cookie(self, cookie: str) -> dict:
        """
        Cookie登录

        cookie: Cookie字符串
        """
        self.cookie = self.data.StrCookieFormat(cookie)
        return self.Status()

    def Status(self) -> dict:
        """
        登录状态

        文档: https://github.com/SocialSisterYi/bilibili-API-collect/blob/master/docs/login/login_info.md
        """
        self.net.RefreshCookie(self.cookie)

        if self.isCheckStatus:
            user = self.net.Response(method="get", url="https://api.bilibili.com/x/web-interface/nav")

            if user["data"]["isLogin"]:
                return self.cookie
            else:
                raise LoginException("登录状态检测失败")

        else:
            logger.info("【登录状态检测】已关闭")
            return self.cookie

    @logger.catch
    def RefreshToken(self) -> bool:
        """
        刷新Token

        https://github.com/SocialSisterYi/bilibili-API-collect/blob/master/docs/login/cookie_refresh.md
        """
        url = ""
        params = {}
        resp = self.net.Response(method="post", url=url, params=params)

        if resp["code"] == 0:
            logger.info("【刷新Token】刷新成功")
            return True
        else:
            logger.error("【刷新Token】刷新失败")
            return False

    @logger.catch
    def ExitLogin(self) -> bool:
        """
        退出登录
        """
        resp = self.net.Response(
            method="post",
            url="https://passport.bilibili.com/login/exit/v2",
            params={"biliCSRF": self.net.GetCookie()["bili_jct"]},
        )

        if resp["code"] == 0:
            logger.info("【退出登录】注销Cookie成功")
            return True
        elif resp["code"] == 2202:
            logger.error("【退出登录】CSRF请求非法")
            return False
        else:
            logger.error("【退出登录】发生了什么")
            return False
