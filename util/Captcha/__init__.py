import time
import os

import browsers
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from loguru import logger


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

        log: 日志实例
        verify: 验证码实例
        gt: 极验gt
        """
        self.verify = verify
        self.gt = gt
        self.rt = "abcdefghijklmnop"  # rt固定即可
        
        self.geetest_path = self.AssestDir("geetest/index.html")

    @logger.catch
    def AssestDir(self, dir: str):
        """
        获取资源文件夹(涉及到Pyinstaller)
        """
        try:
            base_path = sys._MEIPASS  # type: ignore
        except AttributeError:
            base_path = os.getcwd()
        return os.path.join(base_path, dir)

    @logger.catch
    def Geetest(self, challenge: str) -> str:
        """
        极验自动验证
        https://github.com/Amorter/biliTicker_gt

        challenge: 流水号
        返回: validate
        """
        try:
            from bili_ticket_gt_python import ClickPy, SlidePy
        except ImportError:
            logger.error("【登录】导入 bili_ticket_gt_python 库失败, 已自动选择手动验证码验证")
            self.verify = "Manual"

        match self.verify:
            case "Auto":
                return self.Auto(challenge)
            case "Manual":
                return self.Manual(challenge)
            case ClickPy.__name__:
                return self.Auto(challenge)
            case SlidePy.__name__:
                return self.Slide(challenge)
            case _:
                raise Exception("未指定验证码实例或实例类型不正确")

    @logger.catch
    def Auto(self, challenge: str) -> str:
        """
        极验文字点选 - 自动重试

        challenge: 流水号
        返回: validate
        """
        from bili_ticket_gt_python import ClickPy
        
        try:
            validate = ClickPy().simple_match_retry(self.gt, challenge)  # type: ignore
            return validate
        except Exception:
            raise

    @logger.catch
    def Click(self, challenge: str) -> str:
        """
        极验文字点选

        challenge: 流水号
        返回: validate
        """
        from bili_ticket_gt_python import ClickPy
        
        try:
            c, s, args = ClickPy().get_new_c_s_args(self.gt, challenge)  # type: ignore
            before_calculate_key = time.time()
            key = ClickPy().calculate_key(args)  # type: ignore
            w = ClickPy().generate_w(key, self.gt, challenge, str(c), s, self.rt)  # type: ignore
            # 点选验证码生成w后需要等待2秒提交
            w_use_time = time.time() - before_calculate_key
            if w_use_time < 2:
                time.sleep(2 - w_use_time)
            msg, validate = ClickPy().verify(self.gt, challenge, w)  # type: ignore
            logger.info(f"【验证码】验证结果: {msg}")
            return validate
        except Exception:
            raise

    @logger.catch
    def Slide(self, challenge: str) -> str:
        """
        极验滑块

        challenge: 流水号
        返回: validate
        """
        from bili_ticket_gt_python import SlidePy
        
        try:
            c, s, args = SlidePy().get_new_c_s_args(self.gt, challenge)  # type: ignore
            # 注意滑块验证码这里要刷新challenge
            challenge = args[0]
            key = SlidePy().calculate_key(args)  # type: ignore
            w = SlidePy().generate_w(key, self.gt, challenge, str(c), s, self.rt)  # type: ignore
            msg, validate = SlidePy().verify(self.gt, challenge, w)  # type: ignore
            logger.info(f"【验证码】验证结果: {msg}")
            return validate
        except Exception:
            raise

    @logger.catch
    def Manual(self, challenge) -> str:
        """
        手动验证

        challenge: 流水号
        返回: validate
        """
        browser_list = [i for i in list(browsers.browsers()) if i["browser_type"] != "msie"]

        if not browser_list:
            logger.error("【登录】未找到可用浏览器/WebDriver! 建议选择其他方式登录")
            exit()

        selenium_drivers = {
            "chrome": webdriver.Chrome,
            "firefox": webdriver.Firefox,
            "msedge": webdriver.Edge,
            "safari": webdriver.Safari,
        }

        for browser in browser_list:
            browser_type = browser["browser_type"]
            print("请从打开的浏览器中手动验证，获取极验校验值")
            driver = selenium_drivers[browser_type]()

            if not driver:
                logger.error("【登录】所有浏览器/WebDriver尝试登录均失败")
                exit()

            driver.maximize_window()
            try:
                filepath = "file://" + self.geetest_path + "?gt=" + self.gt + "&challenge=" + challenge
                driver.get(filepath)
                wait = WebDriverWait(driver, 30)
                
                event_btn = wait.until(EC.element_to_be_clickable((By.ID, "btn-gen")))
                driver.execute_script("arguments[0].click();", event_btn)

                event_inp = wait.until(EC.visibility_of_element_located((By.ID, "validate")))

                while True:
                    validate = event_inp.get_attribute("value")
                    if validate:
                        break
                return validate

            except Exception as e:
                logger.error(f"【登录】{e}")
                driver.quit()
