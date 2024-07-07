import logging
import sys
import webbrowser
from time import sleep, time

from loguru import logger
from transitions import Machine, State

from util import Bilibili, Captcha, Data, Request


class Task:
    """
    状态机
    """

    @logger.catch
    def __init__(
        self,
        net: Request,
        cap: Captcha,
        api: Bilibili,
        sleep: float = 0.5,
        goldTime: float = 35.0,
        isDebug: bool = False,
    ):
        """
        初始化

        net: 网络实例
        cap: 验证码实例
        api: Bilibili实例
        sleep: 任务间请求间隔时间
        goldTime: 开票黄金时间
        isDebug: 调试模式
        """

        self.net = net
        self.cap = cap
        self.api = api

        self.normalSleep = sleep
        self.goldTime = goldTime

        self.states = [
            State(name="开始"),
            State(name="等待开票", on_enter="WaitAvailableAction"),
            State(name="获取Token", on_enter="QueryTokenAction"),
            State(name="验证码", on_enter="RiskProcessAction"),
            State(name="等待余票", on_enter="QueryTicketAction"),
            State(name="创建订单", on_enter="CreateOrderAction"),
            State(name="创建订单状态", on_enter="CreateStatusAction"),
            State(name="完成"),
        ]

        # 状态机更新时请取消此处及self.DrawFSM()注释以重新生成FSM图
        # from transitions.extensions import GraphMachine
        # self.machine = GraphMachine(
        self.machine = Machine(
            model=self,
            states=self.states,
            initial="开始",
            # show_state_attributes=True,
        )

        self.machine.add_transition(
            trigger="Next",
            source="开始",
            dest="等待开票",
        )

        # 等待开票结束
        self.machine.add_transition(
            trigger="WaitAvailable",
            source="等待开票",
            dest="获取Token",
            conditions=lambda: not self.skipToken,
        )
        self.machine.add_transition(
            trigger="WaitAvailable",
            source="等待开票",
            dest="创建订单",
            conditions=lambda: self.skipToken,
        )

        # 获取Token结束
        self.machine.add_transition(
            trigger="QueryToken",
            source="获取Token",
            dest="创建订单",
            conditions=lambda: self.queryTokenCode == 0,
        )
        self.machine.add_transition(
            trigger="QueryToken",
            source="获取Token",
            dest="验证码",
            conditions=lambda: self.queryTokenCode == -401,
        )
        self.machine.add_transition(
            trigger="QueryToken",
            source="获取Token",
            dest="获取Token",
            conditions=lambda: self.queryTokenCode not in [0, -401],
        )

        # 验证码结束
        self.machine.add_transition(
            trigger="RiskProcess",
            source="验证码",
            dest="获取Token",
            conditions=lambda: self.riskProcessCode == 0,
        )
        self.machine.add_transition(
            trigger="RiskProcess",
            source="验证码",
            dest="验证码",
            conditions=lambda: self.riskProcessCode != 0,
        )

        # 等待余票结束
        self.machine.add_transition(
            trigger="QueryTicket",
            source="等待余票",
            dest="获取Token",
            conditions=lambda: not self.data.TimestampCheck(timestamp=self.refreshTime, duration=self.refreshInterval),
        )
        self.machine.add_transition(
            trigger="QueryTicket",
            source="等待余票",
            dest="创建订单",
            conditions=lambda: self.queryTicketCode,
        )
        self.machine.add_transition(
            trigger="QueryTicket",
            source="等待余票",
            dest="等待余票",
            conditions=lambda: not self.queryTicketCode,
        )

        # 创建订单结束
        self.machine.add_transition(
            trigger="CreateOrder",
            source="创建订单",
            dest="创建订单状态",
            conditions=lambda: self.createOrderCode == 0,
        )
        self.machine.add_transition(
            trigger="CreateOrder",
            source="创建订单",
            dest="获取Token",
            conditions=lambda: self.createOrderCode in range(100050, 100060) or not self.data.TimestampCheck(timestamp=self.refreshTime, duration=self.refreshInterval),
        )
        self.machine.add_transition(
            trigger="CreateOrder",
            source="创建订单",
            dest="等待余票",
            conditions=lambda: self.createOrderCode in [219, 100009] and not self.data.TimestampCheck(timestamp=self.api.saleStart, duration=self.goldTime),
        )
        self.machine.add_transition(
            trigger="CreateOrder",
            source="创建订单",
            dest="创建订单",
            conditions=lambda: self.createOrderCode not in [0, 219, 100009, *range(100050, 100060)] or self.data.TimestampCheck(timestamp=self.api.saleStart, duration=self.goldTime),
        )

        # 创建订单状态结束
        self.machine.add_transition(
            trigger="CreateStatus",
            source="创建订单状态",
            dest="完成",
            conditions=lambda: self.createStatusCode == 0,
        )
        self.machine.add_transition(
            trigger="CreateStatus",
            source="创建订单状态",
            dest="创建订单",
            conditions=lambda: self.createStatusCode != 0,
        )

        # 减速Sleep
        self.slowSleep = 1
        # ERR3 Sleep
        self.errSleep = 4.96
        # 刷新Token间隔
        self.refreshInterval = 7.5
        # 上次刷新Token时间
        self.refreshTime = 0
        # 是否跳过Token获取
        self.skipToken = False
        # 是否已缓存getV2
        self.queryCache = False

        self.data = Data()

        # 取消以绘制FSM图
        # self.DrawFSM()

        if not isDebug:
            # 关闭Transitions自带日志
            logging.getLogger("transitions").setLevel(logging.CRITICAL)

    @logger.catch
    def WaitAvailableAction(self) -> None:
        """
        等待开票
        """
        code, start_time = self.api.GetSaleStartTime()

        match code:
            # 成功
            case 0:
                logger.info(f"【获取开票时间】开票时间为 {self.data.TimestampFormat(int(start_time))}, 当前时间为 {self.data.TimestampFormat(int(time()))}")

            # 不知道
            case _:
                logger.error("【获取开票时间】获取失败!")

        countdown = start_time - int(time())
        logger.info("【等待开票】本机时间已校准!")

        if countdown > 0:
            logger.warning("【等待开票】请确保本机时间是北京时间, 服务器用户尤其要注意!")

            while countdown > 0:
                countdown = start_time - int(time())

                if countdown >= 3600:
                    logger.info(f"【等待开票】需要等待 {countdown/60:.1f} 分钟")
                    sleep(600)
                    countdown -= 600

                elif 3600 > countdown >= 600:
                    logger.info(f"【等待开票】需要等待 {countdown/60:.1f} 分钟")
                    sleep(60)
                    countdown -= 60

                elif 600 > countdown > 60:
                    logger.info(f"【等待开票】准备开票! 需要等待 {countdown/60:.1f} 分钟")
                    sleep(5)
                    countdown -= 5

                elif countdown == 30:
                    logger.info("【等待开票】即将开票! 正在提前获取Token...")
                    self.QueryTokenAction()
                    self.skipToken = True
                    if self.queryTokenCode == -401:
                        self.RiskProcessAction()

                elif 60 > countdown > 1:
                    logger.info(f"【等待开票】即将开票! 需要等待 {countdown-1} 秒")
                    sleep(1)
                    countdown -= 1

                # 准点退出循环
                elif countdown < 1:
                    logger.info("【等待开票】即将开票!")
                    sleep(countdown)

            if countdown == 0:
                logger.info("【等待开票】等待结束! 开始抢票")
        else:
            logger.info("【等待开票】已开票! 开始进入抢票模式")

    @logger.catch
    def QueryTokenAction(self) -> None:
        """
        获取Token
        """
        logger.info("【获取Token】正在刷新Token...")
        self.queryTokenCode, msg = self.api.QueryToken()
        match self.queryTokenCode:
            # 成功
            case 0:
                logger.success("【获取Token】Token获取成功!")
                self.refreshTime = int(time())

            # 验证
            case -401:
                logger.error("【获取Token】需要验证! 下面进入自动过验证")

            # projectID/ScreenId/SkuID错误
            case 100080 | 100082:
                logger.error("【获取Token】项目/场次/价位不存在!")
                logger.warning("程序正在准备退出...")
                sleep(5)
                sys.exit()

            # 停售
            case 100039:
                logger.error("【获取Token】早停售了你抢牛魔呢")
                logger.warning("程序正在准备退出...")
                sleep(5)
                sys.exit()

            # 不知道
            case _:
                logger.error(f"【获取Token】{self.queryTokenCode}: {msg}")

        # 顺路
        if not self.queryCache:
            logger.info("【获取Token】已缓存商品信息")
            self.api.QueryAmount()
            self.queryCache = True

    @logger.catch
    def RiskProcessAction(self) -> None:
        """
        验证
        """
        logger.info("【获取流水】正在尝试获取流水...")
        code, msg, type, data = self.api.RiskInfo()

        # 分类处理
        match code:
            case 0:
                match type:
                    case "geetest":
                        logger.info(f"【验证】验证类型为极验验证码! 流水号: {data}")
                        validate = self.cap.Geetest(data)
                        self.riskProcessCode, msg = self.api.RiskValidate(validate=validate)

                    case "phone":
                        logger.info(f"【验证】验证类型为手机号确认验证! 绑定手机号: {data}")
                        self.riskProcessCode, msg = self.api.RiskValidate(validateMode="phone")

                    case _:
                        logger.error(f"【验证】{type}类型验证暂未支持!")
                        self.riskProcessCode = 114514
                        msg = ""

            # 获取其他地方验证了, 无需验证
            case 100000:
                logger.info("【验证】你是双开/在其他地方验证了吗? 视作已验证处理")
                self.riskProcessCode = 0
                msg = ""

            # 不知道
            case _:
                logger.error(f"【验证】信息获取 {code}: {msg}")
                self.riskProcessCode = 114514
                msg = ""

        # 状态查询
        match self.riskProcessCode:
            # 成功
            case 0:
                logger.info("【验证】验证成功!")

            # 不知道
            case _:
                logger.error(f"【验证】校验 {code}: {msg}")

    @logger.catch
    def QueryTicketAction(self) -> None:
        """
        等待余票
        """
        logger.info("【获取票数】正在蹲票...")
        code, msg, clickable, saleable = self.api.QueryAmount()
        self.queryTicketCode = clickable or saleable

        match code:
            # 成功
            case 0:
                if self.queryTicketCode:
                    logger.success("【等待余票】当前可购买")
                else:
                    logger.warning("【等待余票】当前无票, 系统正在循环蹲票中! 请稍后")
                    # 刷新
                    sleep(self.normalSleep)

            # 太快了
            case 100001:
                logger.error("【等待余票】请求过快, 将减慢请求速度!")
                # 减速
                sleep(self.slowSleep)

            # 不知道
            case _:
                logger.error(f"【等待余票】{code}: {msg}")
                # 刷新
                sleep(self.normalSleep)

    @logger.catch
    def CreateOrderAction(self) -> None:
        """
        创建订单
        """
        logger.info("【创建订单】正在尝试创建订单...")
        self.createOrderCode, msg = self.api.CreateOrder()

        match self.createOrderCode:
            # 成功
            case 0:
                logger.success("【创建订单】订单创建成功!")

            # Token过期
            case x if 100050 <= x <= 100059:
                logger.warning("【创建订单】Token过期! 即将重新获取")

            # 库存不足 219,100009
            case 219 | 100009:
                if self.data.TimestampCheck(timestamp=self.api.saleStart, duration=self.goldTime):
                    logger.warning(f"【创建订单】库存不足! 目前处于开票{self.goldTime}分钟黄金期, 脚本将持续申请下单!")
                else:
                    logger.warning("【创建订单】库存不足!")

                # 规避ERR 3刷新
                sleep(self.errSleep)

            # 存在未付款订单
            case 100079 | 100048:
                logger.error("【创建订单】存在未付款/未完成订单! 请尽快付款")
                # 刷新
                sleep(self.normalSleep)

            # 硬控
            case 3:
                logger.error("【创建订单】被硬控了, 需等待几秒钟")
                # 规避ERR 3刷新
                sleep(self.errSleep)

            # 订单已存在/已购买
            case 100049:
                logger.error("【创建订单】该项目每人限购1张, 已存在购买订单")
                logger.warning("程序正在准备退出...")
                sleep(5)
                sys.exit()

            # 超过购买数量
            case 100098:
                logger.error("【创建订单】该票种已超过可购买数量! 请更换账号或票种")
                logger.warning("程序正在准备退出...")
                sleep(5)
                sys.exit()

            # 本项目需要联系人信息
            case 209001:
                logger.error("【创建订单】目前仅支持实名制一人一票类活动哦~(其他类型活动也用不着上脚本吧啊喂)")
                logger.warning("程序正在准备退出...")
                sleep(5)
                sys.exit()

            # 项目/票种不可售 等待开票
            case 100016 | 100017:
                logger.error("【创建订单】该项目/票种目前不可售!")
                logger.warning("程序正在准备退出...")
                sleep(5)
                sys.exit()

            # 失败
            case _:
                logger.error(f"【创建订单】{self.createOrderCode}: {msg}")
                # 刷新
                sleep(self.normalSleep)

    @logger.catch
    def CreateStatusAction(self) -> None:
        """
        创建订单状态
        """
        code, msg = self.api.CreateOrderStatus()
        match code:
            # 正常
            case 0:
                logger.success("【创建订单状态】锁单成功!")

            # 不知道
            case _:
                logger.error(f"【创建订单状态】{code}: {msg}")

        self.createStatusCode, msg, orderId = self.api.GetOrderStatus()
        match self.createStatusCode:
            # 成功
            case 0:
                logger.success("【获取订单状态】请在打开的浏览器页面进行支付!")
                webbrowser.open(f"https://show.bilibili.com/platform/orderDetail.html?order_id={orderId}")

            # 不知道
            case _:
                logger.error(f"【获取订单状态】{code}: {msg}")

    @logger.catch
    def DrawFSM(self) -> None:
        """
        状态机图输出
        """
        self.machine.get_graph().draw("./assest/fsm.png", prog="dot")

    @logger.catch
    def Run(self) -> bool:
        """
        任务流
        """
        job = {
            "开始": "Next",
            "等待开票": "WaitAvailable",
            "获取Token": "QueryToken",
            "验证码": "RiskProcess",
            "等待余票": "QueryTicket",
            "创建订单": "CreateOrder",
            "创建订单状态": "CreateStatus",
        }

        while self.state != "完成":  # type: ignore
            self.trigger(job[self.state])  # type: ignore
        return True
