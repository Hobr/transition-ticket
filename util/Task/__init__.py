import logging
from time import sleep, time

from loguru import logger
from transitions import Machine, State

from util import Bilibili, Captcha, Request


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
        sleep: int,
    ):
        """
        初始化

        net: 网络实例
        cap: 验证码实例
        api: Bilibili实例
        sleep: 任务间请求间隔时间
        """

        self.net = net
        self.cap = cap
        self.api = api
        self.sleep = sleep

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

        # from transitions.extensions import GraphMachine
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

        self.machine.add_transition(
            trigger="WaitAvailable",
            source="等待开票",
            dest="获取Token",
        )

        # 0-成功, 1-验证码, 2-失败
        self.machine.add_transition(
            trigger="QueryToken",
            source="获取Token",
            dest="创建订单",
            conditions=lambda: self.queryTokenResult == 0,
        )
        self.machine.add_transition(
            trigger="QueryToken",
            source="获取Token",
            dest="验证码",
            conditions=lambda: self.queryTokenResult == 1,
        )
        self.machine.add_transition(
            trigger="QueryToken",
            source="获取Token",
            dest="获取Token",
            conditions=lambda: self.queryTokenResult == 2,
        )

        # True-成功, False-失败
        self.machine.add_transition(
            trigger="RiskProcess",
            source="验证码",
            dest="获取Token",
            conditions=lambda: self.riskProcessResult is True,
        )
        self.machine.add_transition(
            trigger="RiskProcess",
            source="验证码",
            dest="验证码",
            conditions=lambda: self.riskProcessResult is False,
        )

        # True-成功, False-失败
        self.machine.add_transition(
            trigger="QueryTicket",
            source="等待余票",
            dest="创建订单",
            conditions=lambda: self.queryTicketResult is True,
        )
        self.machine.add_transition(
            trigger="QueryTicket",
            source="等待余票",
            dest="等待余票",
            conditions=lambda: self.queryTicketResult is False,
        )

        # 0-成功, 1-刷新, 2-等待, 3-失败
        self.machine.add_transition(
            trigger="CreateOrder",
            source="创建订单",
            dest="创建订单状态",
            conditions=lambda: self.createOrderResult == 0,
        )
        self.machine.add_transition(
            trigger="CreateOrder",
            source="创建订单",
            dest="获取Token",
            conditions=lambda: self.createOrderResult == 1,
        )
        self.machine.add_transition(
            trigger="CreateOrder",
            source="创建订单",
            dest="等待余票",
            conditions=lambda: self.createOrderResult == 2,
        )
        self.machine.add_transition(
            trigger="CreateOrder",
            source="创建订单",
            dest="创建订单",
            conditions=lambda: self.createOrderResult == 3,
        )

        # True-成功, False-失败
        self.machine.add_transition(
            trigger="CreateStatus",
            source="创建订单状态",
            dest="完成",
            conditions=lambda: self.createStatusResult is True,
        )
        self.machine.add_transition(
            trigger="CreateStatus",
            source="创建订单状态",
            dest="创建订单",
            conditions=lambda: self.createStatusResult is False,
        )

        # 是否已缓存getV2
        self.queryCache = False

        # 关闭Transitions自带日志
        logging.getLogger("transitions").setLevel(logging.CRITICAL)

    @logger.catch
    def WaitAvailableAction(self) -> None:
        """
        等待开票
        """
        start_time = self.api.GetSaleStartTime()
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

                elif 600 > countdown >= 60:
                    logger.info(f"【等待开票】准备开票! 需要等待 {countdown/60:.1f} 分钟")
                    sleep(5)
                    countdown -= 5

                elif 60 > countdown >= 1:
                    logger.info(f"【等待开票】即将开票! 需要等待 {countdown} 秒")
                    sleep(1)
                    countdown -= 1

                # 准点退出循环
                elif countdown < 1:
                    sleep(countdown)

            if countdown == 0:
                logger.info("【等待开票】等待结束! 开始抢票")
                # 防止本机时间校准偏移
                sleep(0.003)
        else:
            logger.info("【等待开票】已开票! 开始进入抢票模式")

    @logger.catch
    def QueryTokenAction(self) -> None:
        """
        获取Token

        返回值: 0-成功, 1-风控, 2-未开票, 3-未知
        """
        self.queryTokenResult = self.api.QueryToken()

        # 顺路
        if not self.queryCache:
            logger.info("【刷新Token】已缓存商品信息")
            self.api.QueryAmount()
            self.queryCache = True

        # 防风控
        else:
            sleep(self.sleep)

    @logger.catch
    def RiskProcessAction(self) -> None:
        """
        验证码

        返回值: 0-极验验证, 1手机号验证, 2-取消验证, 3-失败
        """
        match self.api.RiskInfo():
            case 0:
                challenge = self.api.GetRiskChallenge()
                validate = self.cap.Geetest(challenge)
                self.riskProcessResult = self.api.RiskValidate(validate=validate)
            case 1:
                self.riskProcessResult = self.api.RiskValidate(validate_mode="phone")
            case 2:
                self.riskProcessResult = True
            case 3:
                self.riskProcessResult = False

    @logger.catch
    def QueryTicketAction(self) -> None:
        """
        等待余票

        返回值: True-成功, False-失败
        """
        self.queryTicketResult = self.api.QueryAmount()

        if not self.queryTicketResult:
            # 防风控
            sleep(self.sleep)

    @logger.catch
    def CreateOrderAction(self) -> None:
        """
        创建订单

        返回值: 0-成功, 1-刷新, 2-等待, 3-失败
        """
        self.createOrderResult = self.api.CreateOrder()

        if self.createOrderResult != 0:
            # 防风控
            sleep(self.sleep)

    @logger.catch
    def CreateStatusAction(self) -> None:
        """
        创建订单状态

        返回值: True-成功, False-失败
        """
        self.createStatusResult = self.api.GetOrderStatus() if self.api.CreateOrderStatus() else False

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
            sleep(0.15)
            self.trigger(job[self.state])  # type: ignore
        return True
