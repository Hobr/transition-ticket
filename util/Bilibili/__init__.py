import json
import secrets
from base64 import urlsafe_b64encode
from random import randint
from time import time

from loguru import logger

from util.Info import Info
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
        act: dict,
        buyer: dict,
        deliver: dict,
        phone: str,
        userinfo: dict,
        orderType: int = 1,
        count: int = 1,
        cost: int = 0,
    ):
        """
        初始化

        net: 网络实例
        projectId: 项目ID
        screenId: 场次ID
        skuId: 商品ID
        actId: 优惠信息
        buyer: 购买者信息
        deliver: 收货信息
        phone: 手机号
        userinfo: 用户信息
        orderType: 订单类型
        count: 购买数量
        cost: 订单单价
        """
        self.net = net
        self.info = Info(net=net)

        self.scene = "neul-next"

        self.projectId = projectId
        self.screenId = screenId
        self.skuId = skuId
        self.count = count
        self.cost = cost

        self.act = act
        self.buyer = buyer
        self.phone = phone
        self.deliver = deliver
        self.userinfo = userinfo

        self.orderType = orderType
        self.orderId = 0
        self.orderToken = ""
        self.token = ""
        self.risked = False

        self.saleStart = 0
        self.deliverNeed = False
        self.contactNeed = False
        self.deliverFee = 0
        self.payment = 0

        self.buvid = ""
        self.decisionType = ""
        self.ip = ""
        self.mid = ""
        self.ua = ""
        self.voucher = ""
        self.challenge = ""
        self.gt = ""

    @logger.catch
    def RiskInfo(self) -> tuple[int, str, str, str]:
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
            case _:
                type = ""
                dist = ""

        return code, msg, type, dist

    @logger.catch
    def RiskValidate(self, val: str = "", mode: str = "geetest") -> tuple[int, str]:
        """
        校验

        val: 校验值
        mode: 验证方式
        """
        url = "https://api.bilibili.com/x/gaia-vgate/v1/validate"

        match mode:
            case "geetest":
                params = {
                    "challenge": self.challenge,
                    "csrf": self.net.GetCookie()["bili_jct"],
                    "seccode": val + "|jordan",
                    "token": self.token,
                    "validate": val,
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
    def QuerySaleStartTime(self) -> tuple[int, str, int]:
        """
        获取开票时间
        """
        code, msg, skuInfo = self.info.Sku(
            projectId=self.projectId,
            screenId=self.screenId,
            skuId=self.skuId,
            cost=self.cost,
        )

        match code:
            # 成功
            case 0:
                saleStart = skuInfo["sale_start"]
            case _:
                saleStart = 0

        return code, msg, saleStart

    @logger.catch
    def QueryToken(self) -> tuple[int, str]:
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
    def GenerateToken(self) -> tuple[int, str]:
        """
        生成Token

        Base64: URLSafeBase64
        """

        def encrypt(char: int, type: str) -> str:
            """
            加密
            """
            match type:
                # 6 位 timestamp 参数
                case "timestamp":
                    v1 = char.to_bytes(8, "big")
                    v2 = urlsafe_b64encode(v1).decode("utf-8")
                    v3 = v2[5:11]
                    return v3
                # 3 位 projectId 参数
                case "projectId":
                    v1 = char.to_bytes(3, "big")
                    v2 = urlsafe_b64encode(v1).decode("utf-8")
                    v3 = v2[1:4]
                    return v3
                # 4 位 screenId 参数
                case "screenId":
                    v1 = char.to_bytes(4, "big")
                    v2 = urlsafe_b64encode(v1).decode("utf-8")
                    v3 = v2[2:6]
                    return v3
                # 3 位 skuId 参数
                case "skuId":
                    v1 = char.to_bytes(4, "big")
                    v2 = v1[2:4] + b"\x20"
                    v3 = urlsafe_b64encode(v2).decode("utf-8")
                    v4 = v3[0:3]
                    return v4
                case _:
                    return ""

        p1 = "999999"
        # p1 = encrypt(int(time()), "timestamp")
        p2 = encrypt(self.projectId, "projectId")
        p3 = encrypt(self.screenId, "screenId")
        p4 = encrypt(self.skuId, "skuId")
        token = "w" + p1 + "AA" + p2 + "AA" + p3 + "EAAQAJ" + p4 + "."

        if token[7:] == self.token[7:]:
            code = 0
            msg = ""
            self.token = token
        else:
            code = -1
            msg = token

        return code, msg

    @logger.catch
    def QueryAmount(self) -> tuple[int, str, bool, int, int]:
        """
        获取票数
        """
        code, msg, skuInfo = self.info.Sku(
            projectId=self.projectId,
            screenId=self.screenId,
            skuId=self.skuId,
            cost=self.cost,
        )

        match code:
            # 成功
            case 0:
                clickable = skuInfo["clickable"]
                salenum = skuInfo["salenum"]
                num = skuInfo["num"]
            case _:
                clickable = False
                salenum = 4
                num = 0

        return code, msg, clickable, salenum, num

    @logger.catch
    def QueryCacheInfo(self) -> None:
        """
        获取缓存信息

        self.deliverFee: 邮费
        self.deliverNeed: 是否需要邮寄
        self.contactNeed: 是否需要联系人
        """
        _, _, projectInfo = self.info.Project(projectId=self.projectId)
        _, _, screenInfo = self.info.Screen(projectId=self.projectId, screenId=self.screenId)
        _, _, skuInfo = self.info.Sku(projectId=self.projectId, screenId=self.screenId, skuId=self.skuId, cost=self.cost)

        self.saleStart = skuInfo["sale_start"] * 1000
        self.deliverNeed = projectInfo["need_deliver"]
        self.contactNeed = not projectInfo["need_contact"]
        self.deliverFee = max(screenInfo["express_fee"], 0)
        self.payment = self.cost * self.count + self.deliverFee

    @logger.catch
    def CreateOrder(self) -> tuple[int, str]:
        """
        创建订单
        """
        url = "https://show.bilibili.com/api/ticket/order/createV2"
        timestamp = int(round(time() * 1000))
        clickPosition = {
            # "x": randint(1300, 1500),
            "x": randint(600, 1000),
            # "y": randint(20, 100),
            "y": randint(2400, 2500),
            # "origin": timestamp - randint(1500, 10000),
            "origin": max(self.saleStart, timestamp - randint(1500, 10000)),
            "now": timestamp,
        }
        params = {
            "project_id": self.projectId,
            "screen_id": self.screenId,
            "sku_id": self.skuId,
            "count": self.count,
            "pay_money": self.payment,
            "order_type": self.orderType,
            "timestamp": timestamp,
            "buyer_info": json.dumps(self.buyer),
            "token": self.token,
            "deviceId": secrets.token_hex(),
            "clickPosition": clickPosition,
            "requestSource": self.scene,
        }

        # 优惠票
        if self.act:
            params["act_id"] = self.act["act_id"]
            params["order_type"] = self.act["act_type"]

        # 邮寄票
        if self.deliverNeed:
            params["deliver_info"] = json.dumps(self.deliver, ensure_ascii=False)
            params["buyer"] = self.userinfo["username"]
            params["tel"] = self.phone

        # 联系人信息
        if self.contactNeed:
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
                logger.info(f"【创建订单】更新票价为：{(self.payment / 100):.2f}")

            # 未预填收货联系人信息
            case 209001:
                tmp = self.net.Response(
                    method="post",
                    url="https://show.bilibili.com/api/ticket/buyer/saveContactInfo",
                    params={
                        "username": self.userinfo["username"],
                        "tel": self.phone,
                    },
                )
                if tmp["errno"] == 0:
                    self.contactNeed = True
                    logger.info("【创建订单】已自动设置收货联系人信息")

        return code, msg

    @logger.catch
    def CreateOrderStatus(self) -> tuple[int, str]:
        """
        创建订单状态
        """
        url = "https://show.bilibili.com/api/ticket/order/createstatus"
        params = {
            "token": self.orderToken,
            "project_id": self.projectId,
            "orderId": self.orderId,
        }
        res = self.net.Response(method="get", url=url, params=params)
        code = res["errno"]
        msg = res["msg"]

        # 100012: 订单未完成,请等待 且 订单ID相同, 说明订单已经创建
        if code == 100012 and self.orderId == res["data"]["order_id"]:
            code = 0

        return code, msg

    @logger.catch
    def QueryOrderStatus(self) -> tuple[int, str]:
        """
        获取订单状态
        """
        url = "https://show.bilibili.com/api/ticket/order/info"
        params = {
            "order_id": self.orderId,
        }
        res = self.net.Response(method="get", url=url, params=params)
        code = res["errno"]
        msg = res["msg"]

        return code, msg
