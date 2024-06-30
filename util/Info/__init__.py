from loguru import logger

from util import Data, Request


class InfoException(Exception):
    """
    信息错误
    """

    def __init__(self, title: str, message: str):
        self.title = title
        self.message = message
        logger.error(f"【{title}】{message}")


class Info:
    """
    信息
    """

    @logger.catch
    def __init__(self, net: Request, pid: int = 0):
        """
        初始化

        net: 网络实例
        pid: 场次ID
        """
        self.net = net
        self.pid = pid

        self.data = Data()

    def Project(self) -> dict:
        """
        项目基本信息

        接口: GET https://show.bilibili.com/api/ticket/project/getV2?version=134&id=${pid}
        """
        response = self.net.Response(
            method="get",
            url=f"https://show.bilibili.com/api/ticket/project/getV2?version=134&id={self.pid}",
        )

        base_info_id = 0
        for i, item in enumerate(response["data"]["performance_desc"]["list"]):
            if item["module"] == "base_info":
                base_info_id = i
                break

        dist = {
            "id": response["data"]["id"],
            "name": response["data"]["name"],
            "time": response["data"]["performance_desc"]["list"][base_info_id]["details"][0]["content"],
            "start": self.data.TimestampFormat(int(response["data"]["sale_begin"])),
            "end": self.data.TimestampFormat(int(response["data"]["sale_end"])),
            "countdown": self.data.TimestampFormat(int(response["data"]["count_down"]), "s", countdown=True),
        }
        return dist

    def Screen(self) -> dict:
        """
        场次信息

        接口: GET https://show.bilibili.com/api/ticket/project/getV2?version=134&id=${pid}
        """
        response = self.net.Response(
            method="get",
            url=f"https://show.bilibili.com/api/ticket/project/getV2?version=134&id={self.pid}",
        )

        screens = response["data"]["screen_list"]
        if not screens:
            raise InfoException("活动详情", "该活动暂未开放票务信息")

        dist = {}
        for i, screen in enumerate(screens):
            dist[i] = {
                "id": screen["id"],
                "name": screen["name"],
                "display_name": screen["saleFlag"]["display_name"],
                "sale_start": self.data.TimestampFormat(int(screen["sale_start"])),
                "sale_end": self.data.TimestampFormat(int(screen["sale_end"])),
            }
        return dist

    def Sku(self, sid: int) -> dict:
        """
        价格信息

        接口: GET https://show.bilibili.com/api/ticket/project/getV2?version=134&id=${pid}

        sid: 场次ID
        """
        response = self.net.Response(
            method="get",
            url=f"https://show.bilibili.com/api/ticket/project/getV2?version=134&id={self.pid}",
        )

        skus = {}
        for i in response["data"]["screen_list"]:
            if i["id"] == sid:
                skus = i["ticket_list"]
                break

        dist = {}
        for i, sku in enumerate(skus):
            dist[i] = {
                "id": sku["id"],
                "name": f"{sku['screen_name']} - {sku['desc']}",
                "display_name": sku["sale_flag"]["display_name"],
                "price": f"{(sku['price'] / 100):.2f}",
                "sale_start": sku["sale_start"],
                "sale_end": sku["sale_end"],
            }
        return dist

    def Buyer(self) -> list:
        """
        购买人

        接口: GET https://show.bilibili.com/api/ticket/buyer/list?is_default&projectId=${pid}
        """
        response = self.net.Response(
            method="get",
            url="https://show.bilibili.com/api/ticket/buyer/list",
        )

        lists = response["data"]["list"]

        if not lists:
            raise InfoException("购买人", "暂无购买人信息, 请到会员购平台绑定后再次使用!")

        buyers_info = []
        for _i, info in enumerate(lists):
            # 补充/删除信息
            info.pop("error_code")
            info["buyer"] = None
            info["disabledErr"] = None
            info["isBuyerInfoVerified"] = True
            info["isBuyerValid"] = True

            buyer_name = info["name"]
            buyer_id = info["personal_id"]
            buyer_tel = info["tel"]

            buyer_info = {
                "购买人": buyer_name[0] + "*" * 1 + buyer_name[-1],
                "身份证": buyer_id[:6] + "*" * 8 + buyer_id[-4:],
                "手机号": buyer_tel[:3] + "*" * 4 + buyer_tel[-4:],
                "数据": info,
            }
            buyers_info.append(buyer_info)
        return buyers_info

    def UID(self) -> int:
        """
        UID

        接口: GET https://show.bilibili.com/api/ticket/project/getV2?version=134&id=${pid}
        """
        response = self.net.Response(
            method="get",
            url=f"https://show.bilibili.com/api/ticket/project/getV2?version=134&id={self.pid}",
        )
        return response["data"]["mid"]
