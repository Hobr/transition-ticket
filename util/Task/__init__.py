import logging
import sys
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
        sleep: int,
        projectId: int,
        screenId: int,
        skuId: int,
        buyer: dict,
    ):
        """
        初始化

        net: 网络实例
        cap: 验证码实例
        sleep: 任务间请求间隔时间
        projectId: 项目ID
        screenId: 场次ID
        skuId: 商品ID
        buyer: 购买者信息
        """

        self.net = net
        self.cap = cap
        self.sleep = sleep
        self.api = Bilibili(net=self.net, projectId=projectId, screenId=screenId, skuId=skuId, buyer=buyer)

        self.states = [
            State(name="开始"),
            State(name="获取Token", on_enter="QueryTokenAction"),
            State(name="等待开票", on_enter="WaitAvailableAction"),
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
            dest="等待开票",
            conditions=lambda: self.queryTokenResult == 2,
        )
        self.machine.add_transition(
            trigger="QueryToken",
            source="获取Token",
            dest="获取Token",
            conditions=lambda: self.queryTokenResult == 3,
        )

        # True-开票
        self.machine.add_transition(
            trigger="WaitAvailable",
            source="等待开票",
            dest="获取Token",
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

        # 关闭Transitions自带日志
        logging.getLogger("transitions").setLevel(logging.CRITICAL)

    @logger.catch
    def QueryTokenAction(self) -> None:
        """
        获取Token

        返回值: 0-成功, 1-风控, 2-未开票, 3-未知
        """
        self.queryTokenResult = self.api.QueryToken()

        # 顺路
        if self.queryTokenResult == 0:
            self.api.QueryAmount()

        # 防风控
        sleep(self.sleep)

    @logger.catch
    def WaitAvailableAction(self) -> None:
        """
        等待开票
        """
        interval = abs(self.api.GetSaleStartTime() - int(time())) - 30
        countdown = interval

        if countdown >= 3600:
            for _ in range(countdown//10):
                logger.info(f"【等待开票】需要等待 {countdown/60:.1f} 分钟")
                sleep(600)
                countdown -= 600
        if 3600 > countdown >= 600: 
            for _ in range(10):
                logger.info(f"【等待开票】即将开票! 需要等待 {countdown/60:.1f} 分钟")
                sleep(60)
                countdown -=60
        if 600 > countdown >= 60: 
            for _ in range(12):
                logger.info(f"【等待开票】准备开票! 需要等待 {countdown/60:.1f} 分钟")
                sleep(5)
                countdown -=5
        if countdown == 0:
            logger.info("【等待开票】等待结束! 开始抢票")
            
            

    @logger.catch
    def RiskProcessAction(self) -> None:
        """
        验证码

        返回值: True-成功, False-失败
        """
        # 获取流水成功
        if self.api.RiskInfo():
            challenge = self.api.GetRiskChallenge()
            validate = self.cap.Geetest(challenge)
            self.riskProcessResult = self.api.RiskValidate(validate)
        else:
            self.riskProcessResult = False

    @logger.catch
    def QueryTicketAction(self) -> None:
        """
        等待余票

        返回值: True-成功, False-失败
        """
        self.queryTicketResult = self.api.QueryAmount()

        # 防风控
        sleep(self.sleep)

    @logger.catch
    def CreateOrderAction(self) -> None:
        """
        创建订单

        返回值: 0-成功, 1-刷新, 2-等待, 3-失败
        """
        self.createOrderResult = self.api.CreateOrder()

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
            "获取Token": "QueryToken",
            "等待开票": "WaitAvailable",
            "验证码": "RiskProcess",
            "等待余票": "QueryTicket",
            "创建订单": "CreateOrder",
            "创建订单状态": "CreateStatus",
        }
        while self.state != "完成":
            sleep(0.15)
            if self.state in job:
                self.trigger(job[self.state])
            else:
                logger.warning("状态机异常! 程序正在准备退出...")
                sleep(5)
                sys.exit()
        return True
