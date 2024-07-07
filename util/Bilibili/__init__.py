import json
from random import randint
from time import time

from loguru import logger

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
        """
        self.net = net

        self.projectId = projectId
        self.screenId = screenId
        self.skuId = skuId
        self.buyer = buyer
        self.phone = phone

        self.orderType = orderType
        self.count = count

        self.scene = "neul-next"
        self.screenPath = 0
        self.skuPath = 0

        self.risked = False

    @logger.catch
    def GetSaleStartTime(self) -> tuple:
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
            return code, dist
        else:
            return 114514, 0

    @logger.catch
    def QueryToken(self) -> tuple:
        """
        获取Token
        """
        # 成功
        if not self.risked:
            url = f"https://show.bilibili.com/api/ticket/order/prepare?project_id={self.projectId}"

        # 刚刚验证完
        else:
            url = f"https://show.bilibili.com/api/ticket/order/prepare?project_id={self.projectId}&token={self.token}&gaia_vtoken={self.token}"
            self.risked = False

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
                params = {
                    "code": self.phone,
                    "csrf": self.net.GetCookie()["bili_jct"],
                    "token": self.token,
                }

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
                    saleable = path["sale_flag_number"] in [2, 8]  # 2: 可售 4: 已售罄 8: 暂时售罄

                # 没保存Sku位置
                else:
                    for i, screen in enumerate(data["screen_list"]):
                        if screen["id"] == self.screenId:
                            for j, sku in enumerate(screen["ticket_list"]):
                                if sku["id"] == self.skuId:
                                    self.cost = sku["price"]
                                    self.saleStart = sku["saleStart"]
                                    clickable = sku["clickable"]
                                    saleable = sku["sale_flag_number"] in [2, 8]  # 2: 可售 4: 已售罄 8: 暂时售罄
                                    self.screenPath = i
                                    self.skuPath = j
                                    break
            case _:
                clickable = False
                saleable = False

        return code, msg, clickable, saleable

    @logger.catch
    def CreateOrder(self) -> tuple:
        """
        创建订单
        """
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

        return code, msg

    @logger.catch
    def CreateOrderStatus(self) -> tuple:
        """
        创建订单状态
        """
        url = f"https://show.bilibili.com/api/ticket/order/createstatus?token={self.orderToken}&project_id={self.projectId}&orderId={self.orderId}"
        res = self.net.Response(method="get", url=url)
        return res["errno"], res["msg"]

    @logger.catch
    def GetOrderStatus(self) -> tuple:
        """
        获取订单状态
        """
        url = f"https://show.bilibili.com/api/ticket/order/info?order_id={self.orderId}"
        res = self.net.Response(method="get", url=url)
        return res["errno"], res["msg"], self.orderId
