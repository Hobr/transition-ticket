import json
import time
import webbrowser
from random import randint

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

        self.orderType = orderType
        self.count = count

        self.scene = "neul-next"
        self.screenPath = 0
        self.skuPath = 0

        self.data = Data()
        self.risked = False
        self.queryNotice = False
        self.createNotice = False

    @logger.catch
    def QueryToken(self) -> int:
        """
        获取Token

        返回: 0-成功, 1-风控, 2-未知
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
        res = self.net.Response(method="post", url=url, params=params).json()
        data = res["data"]
        code = res["errno"]

        # 成功
        if code == 0:
            logger.info("【获取Token】Token获取成功!")
            self.token = data["token"]
            return 0

        # 风控
        elif code == -401:
            riskParams = data["ga_data"]["riskParams"]
            self.mid = riskParams["mid"]
            self.decisionType = riskParams["decision_type"]
            self.buvid = riskParams["buvid"]
            self.ip = riskParams["ip"]
            self.scene = riskParams["scene"]
            self.ua = riskParams["ua"]
            self.voucher = riskParams["v_voucher"]
            logger.warning("【获取Token】已风控")
            return 1

        # projectID/ScreenId/SkuID错误
        if code in [100080, 100082]:
            logger.error("【获取Token】项目/场次/价位不存在!")
            exit()

        # 没开票
        if code == 100041:
            logger.error("【获取Token】该项目暂未开票!")
            exit()

        # 停售
        if code == 100039:
            logger.error("【获取Token】早停售了你抢牛魔呢")
            exit()

        # 未知
        else:
            logger.error(f"【获取Token】{code}: {res['msg']}")
            return 2

    @logger.catch
    def QueryAmount(self) -> bool:
        """
        获取票数

        返回: True-有票, False-无票
        """
        url = f"https://show.bilibili.com/api/ticket/project/getV2?version=134&id={self.projectId}&project_id={self.projectId}&requestSource={self.scene}"
        res = self.net.Response(method="get", url=url).json()
        data = res["data"]
        code = res["errno"]

        # 成功
        if code == 0:
            # 有保存Sku位置
            if data["screen_list"][self.screenPath]["ticket_list"][self.skuPath]["id"] == self.skuId:
                self.cost = data["screen_list"][self.screenPath]["ticket_list"][self.skuPath]["price"]
                self.saleStart = data["screen_list"][self.screenPath]["ticket_list"][self.skuPath]["saleStart"]
                clickable = data["screen_list"][self.screenPath]["ticket_list"][self.skuPath]["clickable"]

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

            # 有票
            if clickable:
                logger.info("【获取票数】当前可购买")
                return True

            # 无票
            else:
                if not self.queryNotice:
                    logger.warning("【获取票数】当前无票, 系统正在循环蹲票中! 请稍后")
                    self.queryNotice = True
                return False

        # 失败
        else:
            logger.error(f"【获取票数】{code}: {res['msg']}")
            return False

    @logger.catch
    def RiskInfo(self) -> bool:
        """
        获取流水

        返回: True-成功, False-失败
        """
        # 获取CSRF
        if self.csrf is None:
            self.csrf = self.net.GetCookie()["bili_jct"]

        url = "https://api.bilibili.com/x/gaia-vgate/v1/register"
        params = {
            "buvid": self.buvid,
            "csrf": self.csrf,
            "decision_type": self.decisionType,
            "ip": self.ip,
            "mid": self.mid,
            "origin_scene": self.scene,
            "scene": self.scene,
            "ua": self.ua,
            "v_voucher": self.voucher,
        }
        res = self.net.Response(method="post", url=url, params=params).json()
        data = res["data"]
        code = res["code"]

        # 成功
        if code == 0:
            self.token = data["token"]
            self.challenge = data["geetest"]["challenge"]
            self.gt = data["geetest"]["gt"]
            return True

        # 失败
        else:
            logger.error(f"【获取流水】{code}: {res['message']}")
            return False

    @logger.catch
    def GetRiskChallenge(self) -> str:
        """
        获取流水号
        """
        return self.challenge

    @logger.catch
    def RiskValidate(self, validate: str) -> bool:
        """
        校验

        validate: 校验值

        返回值: True-成功, False-失败
        """
        url = "https://api.bilibili.com/x/gaia-vgate/v1/validate"
        params = {
            "challenge": self.challenge,
            "csrf": self.csrf,
            "seccode": validate + "|jordan",
            "token": self.token,
            "validate": validate,
        }
        res = self.net.Response(method="get", url=url, params=params).json()
        code = res["code"]

        # 成功&有效
        if code == 0 and res["data"]["is_valid"] == 1:
            self.risked = True
            cookie = self.net.GetCookie()
            cookie["x-bili-gaia-vtoken"] = self.token
            self.net.RefreshCookie(cookie)
            return True

        # 失败
        else:
            logger.error(f"【校验】{code}: {res['message']}")
            return False

    @logger.catch
    def CreateOrder(self) -> int:
        """
        创建订单

        返回: 0-成功, 1-Token过期, 2-库存不足, 3-失败
        """
        url = f"https://show.bilibili.com/api/ticket/order/createV2?project_id={self.projectId}"
        timestamp = int(round(time.time() * 1000))
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
            "buyer_info": f"[{json.dumps(self.buyer)}]",
            "token": self.token,
            "deviceId": "",
            "clickPosition": json.dumps(clickPosition),
            "newRisk": True,
            "requestSource": self.scene,
        }
        res = self.net.Response(method="post", url=url, params=params).json()
        data = res["data"]
        code = res["errno"]

        # 成功
        if code == 0:
            self.orderId = data["orderId"]
            self.orderToken = data["token"]
            logger.info("【创建订单】订单创建成功!")
            return 0

        # Token过期
        elif "10005" in str(code):
            logger.warning("【创建订单】Token过期! 即将重新获取")
            return 1

        # 库存不足 219,100009
        elif code in [219, 100009]:
            if self.data.TimestampCheck(timestamp=self.saleStart, duration=15):
                if self.createNotice:
                    logger.warning("【创建订单】目前处于开票15分钟黄金期, 已为您忽略无票提示!")
                    self.createNotice = True
                return 3
            else:
                logger.warning("【创建订单】库存不足!")
                return 2

        # 存在未付款订单
        elif code == 100079:
            logger.error("【创建订单】存在未付款订单! 请在支付或取消订单后再次运行")
            exit()

        # 订单已存在/已购买
        elif code == 100049:
            logger.error("【创建订单】该项目每人限购1张, 已存在购买订单")
            exit()

        # 本项目需要联系人信息
        elif code == 209001:
            logger.error("【创建订单】目前仅支持实名制一人一票类活动哦~(其他类型活动也用不着上脚本吧啊喂)")
            exit()

        # 失败
        else:
            if not self.createNotice:
                logger.error(f"【创建订单】{code}: {res['msg']}")
            return 3

    @logger.catch
    def CreateOrderStatus(self) -> bool:
        """
        创建订单状态

        返回: True-成功, False-失败
        """
        url = f"https://show.bilibili.com/api/ticket/order/createstatus?token={self.orderToken}&project_id={self.projectId}&orderId={self.orderId}"
        res = self.net.Response(method="get", url=url).json()
        code = res["errno"]

        # 成功
        if code == 0:
            logger.info("【创建订单状态】锁单成功!")
            return True

        # 失败
        else:
            logger.error(f"【创建订单状态】{code}: {res['msg']}")
            return False

    @logger.catch
    def GetOrderStatus(self) -> bool:
        """
        获取订单状态

        返回: True-成功, False-失败
        """
        url = f"https://show.bilibili.com/api/ticket/order/info?order_id={self.orderId}"
        res = self.net.Response(method="get", url=url).json()
        code = res["errno"]

        # 成功
        if code == 0:
            logger.info("【获取订单状态】请扫码/在打开的浏览器页面进行支付!")
            webbrowser.open(f"https://show.bilibili.com/platform/orderDetail.html?order_id={self.orderId}")
            return True

        # 失败
        else:
            logger.error(f"【获取订单状态】{code}: {res['msg']}")
            return False
