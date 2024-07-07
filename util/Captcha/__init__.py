import sys
from os import getcwd, path
from time import sleep

import browsers
from loguru import logger
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


class Captcha:
    """
    验证
    """

    @logger.catch
    def __init__(
        self,
        verify: str = "Auto",
        gt: str = "ac597a4506fee079629df5d8b66dd4fe",
    ):
        """
        初始化

        verify: 验证方式
        gt: 极验gt
        """
        try:
            from bili_ticket_gt_python import ClickPy

            self.gtPy = ClickPy()
        except ImportError:
            self.verify = "Manual"
            logger.warning("【验证】无法导入极验自动验证，请手动验证")

        self.verify = verify
        self.gt = gt
        self.rt = "abcdefghijklmnop"  # rt固定16位字符串即可

        self.geetest_path = self.AssestDir("geetest/index.html")

    @logger.catch
    def Geetest(self, challenge: str) -> str:
        if self.verify == "Auto":
            return self.Auto(challenge)
        elif self.verify == "Manual":
            return self.Manual(challenge)
        else:
            logger.error("【验证】verify参数错误")
            return ""

    @logger.catch
    def Auto(self, challenge: str) -> str:
        """
        极验自动验证
        https://github.com/Amorter/biliTicker_gt

        challenge: 流水号
        返回: validate
        """
        try:
            validate = self.gtPy.simple_match_retry(self.gt, challenge)
            logger.info(f"【极验文字点选验证】验证结果: {validate}")
            return validate
        except Exception as e:
            logger.error(f"【验证】{e}")
            self.verify = "Manual"
            logger.warning("【验证】无法使用极验自动验证，请手动验证")
            return self.Geetest(challenge)

    @logger.catch
    def Manual(self, challenge) -> str:
        """
        手动验证

        challenge: 流水号
        返回: validate
        """
        browser_list = [i for i in list(browsers.browsers()) if i["browser_type"] != "msie"]

        if not browser_list:
            logger.error("【验证】未找到可用浏览器/WebDriver! 建议选择其他方式登录")

        selenium_drivers = {
            "chrome": webdriver.Chrome,
            "firefox": webdriver.Firefox,
            "msedge": webdriver.Edge,
            "safari": webdriver.Safari,
        }

        for browser in browser_list:
            browser_type = browser["browser_type"]
            print("请从打开的浏览器中手动验证，获取极验校验值")
            print("建议点选文字时，持续两秒以上，以保证能通过校验")
            driver = selenium_drivers[browser_type]()

            if not driver:
                logger.error("【验证】所有浏览器/WebDriver尝试登录均失败")

            driver.maximize_window()
            try:
                filepath = "file://" + self.geetest_path + "?gt=" + self.gt + "&challenge=" + challenge
                driver.get(filepath)
                wait = WebDriverWait(driver, 30)

                event_btn = wait.until(EC.element_to_be_clickable((By.ID, "btn-gen")))
                driver.execute_script("arguments[0].click();", event_btn)
                sleep(0.8)
                event_cap = wait.until(EC.element_to_be_clickable((By.CLASS_NAME, "geetest_btn")))
                driver.execute_script("arguments[0].click();", event_cap)

                event_inp = wait.until(EC.visibility_of_element_located((By.ID, "validate")))

                while True:
                    validate = event_inp.get_attribute("value")
                    if validate:
                        break
                return validate

            except Exception as e:
                logger.error(f"【验证】{e}")
                driver.quit()

        return ""

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
