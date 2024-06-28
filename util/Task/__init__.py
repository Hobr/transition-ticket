import logging
from time import sleep

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

        # 关闭Transitions自带日志
        logging.getLogger("transitions").setLevel(logging.CRITICAL)

    @logger.catch
    def QueryTokenAction(self) -> None:
        """
        获取Token

        返回值: 0-成功, 1-验证码, 2-失败
        """
        self.queryTokenResult = self.api.QueryToken()
        # 顺路
        self.api.QueryAmount()
        sleep(self.sleep)

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
        sleep(self.sleep)

    @logger.catch
    def CreateOrderAction(self) -> None:
        """
        创建订单

        返回值: 0-成功, 1-刷新, 2-等待, 3-失败
        """
        self.createOrderResult = self.api.CreateOrder()
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
            "验证码": "RiskProcess",
            "等待余票": "QueryTicket",
            "创建订单": "CreateOrder",
            "创建订单状态": "CreateStatus",
        }
        while self.state != "完成":  # type: ignore
            sleep(0.15)
            if self.state in job.keys():  # type: ignore
                self.trigger(job[self.state])  # type: ignore
            else:
                raise
        return True
