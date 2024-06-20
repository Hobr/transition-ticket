import json
import re
import time

import browsers
from bili_ticket_gt_python import ClickPy, SlidePy
from loguru import logger
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from util import Captcha, Data, Request


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
        self.click = ClickPy()
        self.slide = SlidePy()

        self.source = "main_web"

    @logger.catch
    def QRCode(self) -> dict:
        """
        扫码登录

        文档: https://github.com/SocialSisterYi/bilibili-API-collect/blob/master/docs/login/login_action/QR.md
        """
        self.net.Response(method="get", url="https://www.bilibili.com/")

        resp = self.net.Response(
            method="get",
            url="https://passport.bilibili.com/x/passport-login/web/qrcode/generate",
        ).json()

        if resp["code"] == 0:
            url = resp["data"]["url"]
            self.data.QRGenerate(url, "qr.jpg")

            while True:
                time.sleep(1.5)
                url = "https://passport.bilibili.com/x/passport-login/web/qrcode/poll?source=main-fe-header&qrcode_key=" + resp["data"]["qrcode_key"]
                respQR = self.net.Response(method="get", url=url).json()

                check = respQR["data"]
                if check["code"] == 0:
                    logger.info("【登录】登录成功")
                    self.cookie = self.net.GetCookie()
                    # 补充Cookie参数
                    # self.cookie = Data().CookieAppend(self.cookie) | self.cookie
                    return self.Status()

                # 未扫描:86101 扫描未确认:86090
                elif check["code"] not in (86101, 86090):
                    logger.error(f"【登录】{check['code']}: {check['message']}")
                    exit()

        else:
            logger.error(f"【登录】服务器不知道送来啥东西{json.dumps(resp, indent=4)}")
            exit()

    @logger.catch
    def Selenium(self) -> dict:
        """
        Selenium登录

        Chrome WebDriver: https://googlechromelabs.github.io/chrome-for-testing/#stable
        """
        browser_list = [i for i in list(browsers.browsers()) if i["browser_type"] != "msie"]

        if browser_list:
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

                if driver:
                    driver.maximize_window()

                    try:
                        driver.get("https://show.bilibili.com/")
                        wait = WebDriverWait(driver, 30)
                        event = wait.until(EC.element_to_be_clickable((By.CLASS_NAME, "nav-header-register")))
                        driver.execute_script("arguments[0].click();", event)
                        break

                    except Exception as e:
                        logger.exception(f"【登录】{e}")
                        driver.quit()

                else:
                    logger.error("【登录】所有浏览器/WebDriver尝试登录均失败")
        else:
            logger.error("【登录】未找到可用浏览器/WebDriver! 建议选择其他方式登录")
            exit()

        while True:
            time.sleep(0.5)
            if driver.page_source is None or "登录" not in driver.page_source:
                break

        logger.info("【登录】登录成功")
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
        ).json()

        if resp["code"] == 0:
            token = resp["data"]["token"]
            challenge = resp["data"]["geetest"]["challenge"]
            validate = Captcha(verify=self.click).Geetest(challenge)
            seccode = validate + "|jordan"
            return token, challenge, validate, seccode
        else:
            raise

    @logger.catch
    def GetPreCaptcha(self) -> tuple:
        """
        获取PreCaptcha验证码并通过Geetest验证

        文档: https://github.com/SocialSisterYi/bilibili-API-collect/blob/master/docs/login/login_action/readme.md
        """
        resp = self.net.Response(
            method="post",
            url="https://passport.bilibili.com/x/safecenter/captcha/pre",
        ).json()

        if resp["code"] == 0:
            token = resp["data"]["recaptcha_token"]
            challenge = resp["data"]["gee_challenge"]
            validate = Captcha(verify=self.click).Geetest(challenge)
            seccode = validate + "|jordan"
            return token, challenge, validate, seccode
        else:
            raise

    @logger.catch
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
        ).json()

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

        resp = self.net.Response(method="post", url="https://passport.bilibili.com/x/passport-login/web/login", params=params).json()

        if resp["code"] == 0:

            if resp["data"]["status"] == 0:
                logger.info("【登录】登录成功")
                self.cookie = self.net.GetCookie()
                return self.Status()

            else:  # 二次短信验证登录
                logger.info("【登录】登录失败, 需要二次验证")

                resp_url = resp["data"]["url"]
                tmp_token_match = re.search(r"tmp_token=(\w{32})", resp_url)
                tmp_token = tmp_token_match.group(1) if tmp_token_match else ""
                scene_match = re.search(r"scene=([^&]+)", resp_url)
                scene = scene_match.group(1) if scene_match else "loginTelCheck"

                info = self.net.Response(
                    method="get",
                    url=f"https://passport.bilibili.com/x/safecenter/user/info?tmp_code={tmp_token}",
                ).json()

                if info["data"]["account_info"]["bind_tel"]:
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
                    ).json()
                    # BUG: -400 Key: 'SendSmsReq.Type' Error:Field validation for 'Type' failed on the 'required' tag
                    if resend["code"] != 0:
                        logger.error(f"【登录】验证码发送失败: {resend['code']} {resend['message']}")
                        exit()
                    logger.info("【登录】验证码发送成功")
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
                        logger.error(f"【登录】未知错误: {resp['data']['status']}")

                    reverify = self.net.Response(method="post", url=url, params=data).json()

                    if reverify["code"] != 0:
                        logger.error(f"【登录】验证码登录失败: {reverify['code']} {reverify['message']}")
                        exit()
                    else:
                        logger.info("【登录】验证码登录成功")
                        self.net.Response(
                            method="post",
                            url="https://passport.bilibili.com/x/passport-login/web/exchange_cookie",
                            params={"source": "risk", "code": reverify["data"]["code"]},
                        ).json()
                        self.cookie = self.net.GetCookie()
                        return self.Status()
                else:
                    logger.info("【登录】手机号未绑定, 请重新选择登录方式")
                    exit()
        else:
            match int(resp["code"]):
                case -105:
                    logger.error("【登录】验证码错误")
                case -400:
                    logger.error("【登录】请求错误")
                case -629:
                    logger.error("【登录】账号或密码错误")
                case -653:
                    logger.error("【登录】用户名或密码不能为空")
                case -662:
                    logger.error("【登录】提交超时,请重新提交")
                case -2001:
                    logger.error("【登录】缺少必要的参数")
                case -2100:
                    logger.error("【登录】需验证手机号或邮箱")
                case 2400:
                    logger.error("【登录】登录秘钥错误")
                case 2406:
                    logger.error("【登录】验证极验服务出错")
                case 86000:
                    logger.error("【登录】RSA解密失败")
                case _:
                    logger.error(f"【发送验证码】{resp['code']} {resp['message']}")
            exit()

    @logger.catch
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
        ).json()

        if resp["code"] == 0:
            logger.info("【登录】验证码发送成功")
            captcha_key = resp["data"]["captcha_key"]
            return captcha_key
        else:
            match int(resp["code"]):
                case -400:
                    logger.error("【发送验证码】请求错误")
                case 1002:
                    logger.error("【发送验证码】手机号码格式错误")
                case 1003:
                    logger.error("【发送验证码】验证码已经发送")
                case 86203:
                    logger.error("【发送验证码】短信发送次数已达上限")
                case 2406:
                    logger.error("【发送验证码】验证极验服务出错")
                case 2400:
                    logger.error("【发送验证码】登录秘钥错误")
                case _:
                    logger.error(f"【发送验证码】{resp['code']} {resp['message']}")
            return ""

    @logger.catch
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
        ).json()

        if resp["code"] == 0:
            logger.info("【登录】登录成功")
        else:
            match int(resp["code"]):
                case 1006:
                    logger.error("【登录】请输入正确的短信验证码")
                case 1007:
                    logger.error("【登录】短信验证码已过期")
                case -400:
                    logger.error("【登录】请求错误")
                case _:
                    logger.error(f"【发送验证码】{resp['code']} {resp['message']}")
            raise Exception("手机号验证码登录失败")

        self.cookie = self.net.GetCookie()
        return self.Status()

    @logger.catch
    def Cookie(self, cookie: str) -> dict:
        """
        Cookie登录

        cookie: Cookie字符串
        """
        self.cookie = self.data.StrCookieFormat(cookie)
        return self.Status()

    @logger.catch
    def Status(self) -> dict:
        """
        登录状态

        文档: https://github.com/SocialSisterYi/bilibili-API-collect/blob/master/docs/login/login_info.md
        """
        self.net.RefreshCookie(self.cookie)

        if self.isCheckStatus:
            user = self.net.Response(method="get", url="https://api.bilibili.com/x/web-interface/nav").json()

            if user["data"]["isLogin"]:
                return self.cookie
            else:
                logger.error("【登录状态检测】登录失败")
                exit()

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
        resp = self.net.Response(method="post", url=url, params=params).json()

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
            method="get",
            url="https://passport.bilibili.com/login/exit/v2",
            params={"biliCSRF": self.cookie["bili_jct"]},
        ).json()

        if resp["code"] == 0 and resp["status"]:
            logger.info("【退出登录】注销Cookie成功")
            return True
        elif resp["code"] == 2202:
            logger.error("【退出登录】CSRF请求非法")
            return False
        else:
            logger.error("【退出登录】发生了什么")
            return False
