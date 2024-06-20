import time

from bili_ticket_gt_python import ClickPy, SlidePy
from loguru import logger


class Captcha:
    """
    验证
    """

    @logger.catch
    def __init__(
        self,
        verify: SlidePy | ClickPy | None = None,
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

    @logger.catch
    def Geetest(self, challenge: str) -> str:
        """
        极验自动验证
        https://github.com/Amorter/biliTicker_gt

        challenge: 流水号
        返回: validate
        """
        if isinstance(self.verify, ClickPy):
            return self.Auto(challenge)
        elif isinstance(self.verify, SlidePy):
            return self.Slide(challenge)
        else:
            raise Exception("未指定验证码实例或实例类型不正确")

    @logger.catch
    def Auto(self, challenge: str) -> str:
        """
        极验文字点选 - 自动重试

        challenge: 流水号
        返回: validate
        """
        try:
            validate = self.verify.simple_match_retry(self.gt, challenge)  # type: ignore
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
        try:
            c, s, args = self.verify.get_new_c_s_args(self.gt, challenge)  # type: ignore
            before_calculate_key = time.time()
            key = self.verify.calculate_key(args)  # type: ignore
            w = self.verify.generate_w(key, self.gt, challenge, str(c), s, self.rt)  # type: ignore
            # 点选验证码生成w后需要等待2秒提交
            w_use_time = time.time() - before_calculate_key
            if w_use_time < 2:
                time.sleep(2 - w_use_time)
            msg, validate = self.verify.verify(self.gt, challenge, w)  # type: ignore
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
        try:
            c, s, args = self.verify.get_new_c_s_args(self.gt, challenge)  # type: ignore
            # 注意滑块验证码这里要刷新challenge
            challenge = args[0]
            key = self.verify.calculate_key(args)  # type: ignore
            w = self.verify.generate_w(key, self.gt, challenge, str(c), s, self.rt)  # type: ignore
            msg, validate = self.verify.verify(self.gt, challenge, w)  # type: ignore
            logger.info(f"【验证码】验证结果: {msg}")
            return validate
        except Exception:
            raise

    @logger.catch
    def Manual(self) -> str:
        """
        手动验证
        """
        validate = ""
        return validate
