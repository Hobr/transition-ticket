import re

from loguru import logger

from util import Config, Data, Info, Request


class ProductCli:
    """
    商品配置交互
    """

    @logger.catch
    def __init__(self, conf: Config):
        """
        初始化

        conf: 配置实例
        """
        self.conf = conf

        self.data = Data()
        self.net = Request()
        self.info = Info(net=self.net)

        # 配置
        self.config = {
            # 活动ID
            "projectId": 0,
            # 场次ID
            "screenId": 0,
            # 价格ID
            "skuId": 0,
        }

    @logger.catch
    def Select(self, selects: list) -> dict:
        """
        选择配置

        selects: 可选择项目
        """
        selects.append("新建配置")
        select = self.data.Inquire(type="List", message="请选择加载的商品配置", choices=selects)

        if select == "新建配置":
            return self.Generate()

        else:
            self.config = self.conf.Load(filename=select)
            return self.config

    @logger.catch
    def Generate(self) -> dict:
        """
        生成配置
        """

        @logger.catch
        def ProjectStep() -> int:
            """
            活动
            """
            print("[!] BW2024链接: show.bilibili.com/platform/detail.html?id=85939")
            url = self.data.Inquire(
                type="Text",
                message="请粘贴要抢的活动的网页链接",
            )

            match = re.search(r"id=(\d+)", url)
            if match:
                projectId = match.group(1)
                return int(projectId)

            else:
                logger.error("【商品配置初始化】活动URL格式错误!")
                return ProjectStep()

        @logger.catch
        def ScrenStep() -> int:
            """
            场次
            """
            projectInfo = self.info.Project()
            screenInfo = self.info.Screen()

            lists = {f"{screenInfo[i]['name']} ({screenInfo[i]['display_name']})": screenInfo[i]["id"] for i in screenInfo}
            select = self.data.Inquire(
                type="List",
                message=f"您选择的活动是:{projectInfo['name']}, 接下来请选择场次",
                choices=list(lists.keys()),
            )
            return lists[select]

        @logger.catch
        def SkuStep(screenId: int) -> int:
            """
            价位

            screenId: 场次ID
            """
            skuInfo = self.info.Sku(screenId)
            lists = {(f"{skuInfo[i]['name']} {skuInfo[i]['price']}元 " f"({skuInfo[i]['display_name']})"): skuInfo[i]["id"] for i in skuInfo}
            select = self.data.Inquire(
                type="List",
                message="请选择价位",
                choices=list(lists.keys()),
            )
            return lists[select]

        @logger.catch
        def FilenameStep(name: str) -> str:
            """
            文件名

            skuid: 价位ID
            """
            filename = self.data.Inquire(
                type="Text",
                message="保存的商品文件名称",
                default=name,
            )
            return filename

        print("下面开始配置商品!")
        self.config["projectId"] = ProjectStep()
        self.info = Info(net=self.net, pid=self.config["projectId"])
        self.config["screenId"] = ScrenStep()
        self.config["skuId"] = SkuStep(screenId=self.config["screenId"])

        self.conf.Save(FilenameStep(name=self.info.Project()["name"]), self.config)
        logger.info("【商品配置初始化】配置已保存!")
        return self.config
