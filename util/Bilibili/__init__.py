import json
import sys
import webbrowser
from random import randint
from time import sleep, time

from loguru import logger

from util.Data import Data
from util.Request import Request


class Bilibili:
    """
    会员购
    """

    @logger.catch
    def __init__(
        self,
        net: Request,
        projectId: int,
        screenId: int,
        skuId: int,
        buyer: dict,
        phone: str,
        orderType: int = 1,
        count: int = 1,
        goldTime: float = 35.0,
    ):
        """
        初始化

        net: 网络实例
        projectId: 项目ID
        screenId: 场次ID
        skuId: 商品ID
        buyer: 购买者信息
        orderType: 订单类型
        count: 购买数量
        goldTime: 开票黄金时间
        """
        self.net = net

        self.projectId = projectId
        self.screenId = screenId
        self.skuId = skuId
        self.buyer = buyer
        self.phone = phone

        self.orderType = orderType
        self.count = count
        self.goldTime = goldTime

        self.scene = "neul-next"
        self.screenPath = 0
        self.skuPath = 0

        self.data = Data()
        self.risked = False

    @logger.catch
    def GetSaleStartTime(self) -> int:
        """
        获取开票时间
        """
        url = f"https://show.bilibili.com/api/ticket/project/getV2?version=134&id={self.projectId}&project_id={self.projectId}&requestSource={self.scene}"
        res = self.net.Response(method="get", url=url)
        code = res["errno"]

        # 成功
        if code == 0:
            for _i, screen in enumerate(res["data"]["screen_list"]):
                if screen["id"] == self.screenId:
                    for _j, sku in enumerate(screen["ticket_list"]):
                        if sku["id"] == self.skuId:
                            dist = sku["saleStart"]
                            break
            logger.info(f"【获取开票时间】开票时间为 {self.data.TimestampFormat(int(dist))}, 当前时间为 {self.data.TimestampFormat(int(time()))}")
            return dist
        else:
            logger.error("【获取开票时间】获取失败!")
            return 0

    @logger.catch
    def QueryToken(self) -> tuple:
        """
        获取Token
        """
        logger.info("【获取Token】正在尝试获取Token...")

        # 成功
        if not self.risked:
            url = f"https://show.bilibili.com/api/ticket/order/prepare?project_id={self.projectId}"

        # 刚刚验证完
        else:
            url = f"https://show.bilibili.com/api/ticket/order/prepare?project_id={self.projectId}&token={self.token}&gaia_vtoken={self.token}"

        params = {
            "project_id": self.projectId,
            "screen_id": self.screenId,
            "sku_id": self.skuId,
            "count": self.count,
            "order_type": self.orderType,
            "token": "",
            "requestSource": self.scene,
            "newRisk": True,
        }
        res = self.net.Response(method="post", url=url, params=params)
        code = res["errno"]
        msg = res["msg"]

        # 处理
        match code:
            # 成功
            case 0:
                self.token = res["data"]["token"]
            # 验证
            case -401:
                riskParams = res["data"]["ga_data"]["riskParams"]
                self.mid = riskParams["mid"]
                self.decisionType = riskParams["decision_type"]
                self.buvid = riskParams["buvid"]
                self.ip = riskParams["ip"]
                self.scene = riskParams["scene"]
                self.ua = riskParams["ua"]
                self.voucher = riskParams["v_voucher"]

        return code, msg

    @logger.catch
    def RiskInfo(self) -> tuple:
        """
        获取流水
        """
        logger.info("【获取流水】正在尝试获取流水...")

        url = "https://api.bilibili.com/x/gaia-vgate/v1/register"
        params = {
            "buvid": self.buvid,
            "csrf": self.net.GetCookie()["bili_jct"],
            "decision_type": self.decisionType,
            "ip": self.ip,
            "mid": self.mid,
            "origin_scene": self.scene,
            "scene": self.scene,
            "ua": self.ua,
            "v_voucher": self.voucher,
        }
        res = self.net.Response(method="post", url=url, params=params)
        code = res["code"]
        msg = res["message"]

        # 处理
        match code:
            # 成功
            case 0:
                data = res["data"]
                self.token = data["token"]
                type = data["type"]

                match type:
                    case "geetest":
                        self.challenge = data["geetest"]["challenge"]
                        self.gt = data["geetest"]["gt"]
                        dist = self.challenge
                    case "phone":
                        dist = data["phone"]["tel"]

                    case _:
                        dist = ""

            # 不知道
            case _:
                type = ""
                dist = ""

        return code, msg, type, dist

    @logger.catch
    def RiskValidate(self, validate: str = "", validateMode: str = "geetest") -> tuple:
        """
        校验

        validate: 校验值
        validateMode: 验证方式
        """
        url = "https://api.bilibili.com/x/gaia-vgate/v1/validate"

        # 处理
        match validateMode:
            case "geetest":
                params = {
                    "challenge": self.challenge,
                    "csrf": self.net.GetCookie()["bili_jct"],
                    "seccode": validate + "|jordan",
                    "token": self.token,
                    "validate": validate,
                }

            case "phone":
                if self.phone != "":
                    params = {
                        "code": self.phone,
                        "csrf": self.net.GetCookie()["bili_jct"],
                        "token": self.token,
                    }
                else:
                    logger.error("【验证】你没有配置实名手机号! 怎么办呢?")

            case _:
                logger.error("【验证】这是什么验证类型?")

        res = self.net.Response(method="get", url=url, params=params)
        code = res["code"]
        msg = res["message"]

        # 成功&有效
        if code == 0 and res["data"]["is_valid"] == 1:
            self.risked = True
            cookie = self.net.GetCookie()
            cookie["x-bili-gaia-vtoken"] = self.token
            self.net.RefreshCookie(cookie)

        return code, msg

    @logger.catch
    def QueryAmount(self) -> tuple:
        """
        获取票数
        """
        logger.info("【获取票数】正在蹲票...")
        url = f"https://show.bilibili.com/api/ticket/project/getV2?version=134&id={self.projectId}&project_id={self.projectId}&requestSource={self.scene}"
        res = self.net.Response(method="get", url=url)
        code = res["errno"]
        msg = res["msg"]

        match code:
            # 成功
            case 0:
                data = res["data"]
                path = data["screen_list"][self.screenPath]["ticket_list"][self.skuPath]

                # 有保存Sku位置
                if path["id"] == self.skuId:
                    self.cost = path["price"]
                    self.saleStart = path["saleStart"]
                    clickable = path["clickable"]

                # 没保存Sku位置
                else:
                    for i, screen in enumerate(data["screen_list"]):
                        if screen["id"] == self.screenId:
                            for j, sku in enumerate(screen["ticket_list"]):
                                if sku["id"] == self.skuId:
                                    self.cost = sku["price"]
                                    self.saleStart = sku["saleStart"]
                                    clickable = sku["clickable"]
                                    self.screenPath = i
                                    self.skuPath = j
                                    break
            case _:
                clickable = False

        return code, msg, clickable

    @logger.catch
    def CreateOrder(self) -> tuple:
        """
        创建订单
        """
        logger.info("【创建订单】正在尝试创建订单...")
        url = f"https://show.bilibili.com/api/ticket/order/createV2?project_id={self.projectId}"
        timestamp = int(round(time() * 1000))
        clickPosition = {
            "x": randint(1300, 1500),
            "y": randint(20, 100),
            "origin": timestamp - randint(2500, 10000),
            "now": timestamp,
        }
        params = {
            "project_id": self.projectId,
            "screen_id": self.screenId,
            "sku_id": self.skuId,
            "count": self.count,
            "pay_money": self.cost * self.count,
            "order_type": self.orderType,
            "timestamp": timestamp,
            "buyer_info": json.dumps(self.buyer),
            "token": self.token,
            "deviceId": "",
            "clickPosition": clickPosition,
            "newRisk": True,
            "requestSource": self.scene,
        }
        res = self.net.Response(method="post", url=url, params=params)
        code = res["errno"]
        msg = res["msg"]

        # 成功
        if code == 0:
            self.orderId = res["data"]["orderId"]
            self.orderToken = res["data"]["token"]
            logger.success("【创建订单】订单创建成功!")

        # Token过期
        elif "10005" in str(code):
            logger.warning("【创建订单】Token过期! 即将重新获取")

        # 库存不足 219,100009
        elif code in [219, 100009]:
            if self.data.TimestampCheck(timestamp=self.saleStart, duration=self.goldTime):
                logger.warning(f"【创建订单】目前处于开票{self.goldTime}分钟黄金期, 已为您忽略无票提示!")
            else:
                logger.warning("【创建订单】库存不足!")

        # 存在未付款订单
        elif code in [100079, 100048]:
            logger.error("【创建订单】存在未付款/未完成订单! 请尽快付款")

        # 硬控
        elif code == 3:
            logger.error("【创建订单】被硬控了, 需等待几秒钟")

        # 订单已存在/已购买
        elif code == 100049:
            logger.error("【创建订单】该项目每人限购1张, 已存在购买订单")
            logger.warning("程序正在准备退出...")
            sleep(5)
            sys.exit()

        # 本项目需要联系人信息
        elif code == 209001:
            logger.error("【创建订单】目前仅支持实名制一人一票类活动哦~(其他类型活动也用不着上脚本吧啊喂)")
            logger.warning("程序正在准备退出...")
            sleep(5)
            sys.exit()

        # 项目/票种不可售 等待开票
        elif code in [100016, 100017]:
            logger.error("【创建订单】该项目/票种目前不可售!")
            logger.warning("程序正在准备退出...")
            sleep(5)
            sys.exit()

        # 失败
        else:
            logger.error(f"【创建订单】{code}: {msg}")

        return code, msg

    @logger.catch
    def CreateOrderStatus(self) -> tuple:
        """
        创建订单状态
        """
        url = f"https://show.bilibili.com/api/ticket/order/createstatus?token={self.orderToken}&project_id={self.projectId}&orderId={self.orderId}"
        res = self.net.Response(method="get", url=url)
        code = res["errno"]
        msg = res["msg"]

        # 成功
        if code == 0:
            logger.success("【创建订单状态】锁单成功!")

        # 失败
        else:
            logger.error(f"【创建订单状态】{code}: {msg}")

        return code, msg

    @logger.catch
    def GetOrderStatus(self) -> tuple:
        """
        获取订单状态
        """
        url = f"https://show.bilibili.com/api/ticket/order/info?order_id={self.orderId}"
        res = self.net.Response(method="get", url=url)
        code = res["errno"]
        msg = res["msg"]

        # 成功
        if code == 0:
            logger.success("【获取订单状态】请在打开的浏览器页面进行支付!")
            webbrowser.open(f"https://show.bilibili.com/platform/orderDetail.html?order_id={self.orderId}")

        # 失败
        else:
            logger.error(f"【获取订单状态】{code}: {msg}")

        return code, msg
