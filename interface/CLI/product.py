import re
import sys
from time import sleep

from loguru import logger

from util import Config, Data, Info, Request
from util.Info import InfoException


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

        # 颜色ANSI代码
        self.YELLOW = "\033[93m"
        self.BLUE = "\033[96m"
        self.RESET = "\033[0m"

    @logger.catch
    def Select(self, selects: list) -> dict:
        """
        选择配置

        selects: 可选择项目
        """
        if selects[-1] != "新建商品配置":
            selects.append("新建商品配置")

        select = self.data.Inquire(type="List", message="请选择加载的商品配置", choices=selects)

        if select == "新建商品配置":
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
            print(f"{self.BLUE}[{self.YELLOW}!{self.BLUE}]{self.RESET} BW2024链接: show.bilibili.com/platform/detail.html?id=85939")
            print(f"{self.BLUE}[{self.YELLOW}!{self.BLUE}]{self.RESET} BML2024链接: show.bilibili.com/platform/detail.html?id=85938")
            url = self.data.Inquire(
                type="Text",
                message="请粘贴要抢的活动的网页链接",
            )

            try:
                match = re.search(r"id=(\d+)", url)
                if match:
                    projectId = match.group(1)
                    return int(projectId)
                else:
                    raise InfoException("商品配置初始化", "活动URL格式错误!")

            except InfoException:
                logger.warning("请重新配置活动信息!")
                return ProjectStep()

        @logger.catch
        def ScreenStep() -> int:
            """
            场次
            """
            try:
                projectInfo = self.info.Project()
                screenInfo = self.info.Screen()

                lists = {
                    f"{self.YELLOW if screenInfo[i]['display_name'] == '预售中' else ''}"
                    f"{screenInfo[i]['name']} ({screenInfo[i]['display_name']})"
                    f"{self.RESET if screenInfo[i]['display_name'] == '预售中' else ''}": screenInfo[i]["id"]
                    for i in range(len(screenInfo))
                }
                select = self.data.Inquire(
                    type="List",
                    message=f"您选择的活动是:{projectInfo['name']}, 接下来请选择场次",
                    choices=list(lists.keys()),
                )
                return lists[select]

            except InfoException:
                logger.exception("请重新配置活动信息!")
                logger.warning("程序正在准备退出...")
                sleep(5)
                sys.exit()

        @logger.catch
        def SkuStep(screenId: int) -> tuple:
            """
            价位

            screenId: 场次ID
            """
            try:
                skuInfo = self.info.Sku(screenId)
                lists = {
                    f"{self.YELLOW if skuInfo[i]['display_name'] == '预售中' else ''}"
                    f"{skuInfo[i]['name']} {skuInfo[i]['price']}元 ({skuInfo[i]['display_name']})"
                    f"{self.RESET}": skuInfo[i]["id"]
                    for i in range(len(skuInfo))
                }
                select = self.data.Inquire(
                    type="List",
                    message="请选择价位",
                    choices=list(lists.keys()),
                )
                return lists[select], select.split("(")[0].strip().replace(self.YELLOW, "").replace(self.RESET, "")

            except InfoException:
                logger.exception("请重新配置活动信息!")
                logger.warning("程序正在准备退出...")
                sleep(5)
                sys.exit()

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
        self.config["screenId"] = ScreenStep()
        skuId, skuSelected = SkuStep(screenId=self.config["screenId"])
        self.config["skuId"] = skuId

        self.conf.Save(FilenameStep(name=f"{self.info.Project()['name']} ({skuSelected})"), self.config)
        logger.info("【商品配置初始化】配置已保存!")
        return self.config
