import json
import secrets
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
        deliver: dict,
        phone: str,
        userinfo: dict,
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
        deliver: 收货信息
        phone: 手机号
        userinfo: 用户信息
        orderType: 订单类型
        count: 购买数量
        """
        self.net = net

        self.projectId = projectId
        self.screenId = screenId
        self.skuId = skuId
        self.buyer = buyer
        self.phone = phone
        self.userinfo = userinfo

        self.orderType = orderType
        self.count = count

        self.scene = "neul-next"
        self.screenPath = 0
        self.skuPath = 0

        self.cost = 0
        self.orderId = 0
        self.orderToken = ""
        self.risked = False

        self.deliver = deliver
        self.deliverNeed = False
        self.ContactNeed = False
        self.deliverFee = 0
        self.payment = 0

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
            self.deliverNeed = res["data"]["has_paper_ticket"]
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
                params = {}
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
                    clickable = path["clickable"]
                    salenum = path["sale_flag_number"]
                    num = path["num"]

                # 没保存Sku位置
                else:
                    for i, screen in enumerate(data["screen_list"]):
                        if screen["id"] == self.screenId:
                            for j, sku in enumerate(screen["ticket_list"]):
                                if sku["id"] == self.skuId:
                                    clickable = sku["clickable"]
                                    salenum = sku["sale_flag_number"]
                                    num = sku["num"]
                                    self.screenPath = i
                                    self.skuPath = j
                                    break
            case _:
                clickable = False
                salenum = 4
                num = 0

        return code, msg, clickable, salenum, num

    @logger.catch
    def QueryPrice(self) -> None:
        """
        获取价格
        self.cost: 票价
        self.deliverFee: 邮费
        """
        url = f"https://show.bilibili.com/api/ticket/project/getV2?version=134&id={self.projectId}&project_id={self.projectId}&requestSource={self.scene}"
        res = self.net.Response(method="get", url=url)
        code = res["errno"]

        match code:
            # 成功
            case 0:
                data = res["data"]
                screen = data["screen_list"][self.screenPath]
                sku = data["screen_list"][self.screenPath]["ticket_list"][self.skuPath]

                # 有保存Screen位置
                if screen["id"] == self.skuId:
                    self.deliverFee = max(screen["express_fee"], 0)

                # 有保存Sku位置
                if sku["id"] == self.skuId:
                    self.cost = sku["price"]

                # 没保存Screen/Sku位置
                else:
                    for _i, screen in enumerate(data["screen_list"]):
                        if screen["id"] == self.screenId:
                            self.deliverFee = max(screen["express_fee"], 0)

                            for _j, sku in enumerate(screen["ticket_list"]):
                                if sku["id"] == self.skuId:
                                    self.cost = sku["price"]
                                    break

                            break
            case _:
                self.cost = 0
                self.deliverFee = 0

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
            "pay_money": self.cost * self.count + self.deliverFee,
            "order_type": self.orderType,
            "timestamp": timestamp,
            "buyer_info": json.dumps(self.buyer),
            "token": self.token,
            "deviceId": secrets.token_hex(),
            "clickPosition": clickPosition,
            "requestSource": self.scene,
        }

        # 邮寄票
        if self.deliverNeed:
            params["deliver_info"] = json.dumps(self.deliver, ensure_ascii=False)
            params["pay_money"] = max(self.cost * self.count + self.deliverFee, self.payment)
            params["buyer"] = self.userinfo["username"]
            params["tel"] = self.phone

        # 联系人信息
        if self.ContactNeed:
            params["buyer"] = self.userinfo["username"]
            params["tel"] = self.phone

        res = self.net.Response(method="post", url=url, params=params)
        code = res["errno"]
        msg = res["msg"]

        match code:
            # 成功
            case 0:
                self.orderId = res["data"]["orderId"]
                self.orderToken = res["data"]["token"]

            # 存在订单
            case 100079:
                self.orderId = res["data"]["orderId"]

            # 票价错误
            case 100034:
                self.payment = res["data"]["pay_money"]
                logger.info(f"【创建订单】更新票价为：{self.payment / 100}")

            # 未预填收货联系人信息
            case 209001:
                self.ContactNeed = True
                tmp = self.net.Response(
                    method="post",
                    url="https://show.bilibili.com/api/ticket/buyer/saveContactInfo",
                    params={"username": self.userinfo["username"], "tel": self.phone},
                )
                if tmp["errno"] == 0:
                    logger.info("【创建订单】已自动设置收货联系人信息")

        return code, msg

    @logger.catch
    def CreateOrderStatus(self) -> tuple:
        """
        创建订单状态
        """
        url = f"https://show.bilibili.com/api/ticket/order/createstatus?token={self.orderToken}&project_id={self.projectId}&orderId={self.orderId}"
        res = self.net.Response(method="get", url=url)
        code = res["errno"]

        # 100012: 订单未完成,请等待 且 订单ID相同, 说明订单已经创建
        if code == 100012 and self.orderId == res["data"]["order_id"]:
            code = 0

        return code, res["msg"]

    @logger.catch
    def GetOrderStatus(self) -> tuple:
        """
        获取订单状态
        """
        url = f"https://show.bilibili.com/api/ticket/order/info?order_id={self.orderId}"
        res = self.net.Response(method="get", url=url)
        return res["errno"], res["msg"]
