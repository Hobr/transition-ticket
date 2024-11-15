import logging
import sys
import threading
import webbrowser
from time import sleep, time

from loguru import logger
from transitions import Machine, State

from util import Bilibili, Captcha, Data, Notice, Request


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
        notice: dict,
        sleep: float = 0.5,
        isDebug: bool = False,
    ):
        """
        初始化

        net: 网络实例
        cap: 验证码实例
        api: Bilibili实例
        notice: 通知设置
        sleep: 默认请求间请求间隔时间
        isDebug: 调试模式
        """
        self.net = net
        self.cap = cap
        self.api = api

        self.notice = notice
        self.sleep = sleep

        self.data = Data()
        self.queryCache = False

        # 重试创建订单间隔
        self.refreshInterval = 2.1
        # 上次重试创建订单时间
        self.refreshTime = 0

        # 上次有票时间
        self.availableTime = 0
        # 有票期内间隔
        self.availableSchedule = [
            # 0-0
            [0, 0.0],
            # 0-1.25
            [1.25, self.sleep / 1.5],
            # 1.25-5
            [5.0, self.sleep],
            # 5-8
            [8, self.sleep * 1.5],
            # 8-10.5
            [10.5, self.sleep / 1.5],
        ]

        # Code
        self.skipToken = False
        self.countdownOver = False
        self.queryTokenCode = 114514
        self.riskProcessCode = 114514
        self.queryTicketCode = False
        self.createOrderCode = 114514
        self.createStatusCode = 114514

        self.states = [
            State(name="开始"),
            State(name="等待开票", on_enter="WaitAvailableAction"),
            State(name="获取Token", on_enter="QueryTokenAction"),
            State(name="验证码", on_enter="RiskProcessAction"),
            State(name="等待余票", on_enter="QueryTicketAction"),
            State(name="创建订单", on_enter="CreateOrderAction"),
            State(name="创建订单状态", on_enter="CreateStatusAction"),
            State(name="完成", on_enter="FinishAction"),
        ]

        # 状态机更新时请取消此处及self.DrawFSM()注释以重新生成FSM图
        # from transitions.extensions import GraphMachine

        # 状态机状态网页显示体验
        # from transitions_gui import WebMachine

        # self.machine = GraphMachine(
        # self.machine = WebMachine(
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
        )

        # 获取Token结束
        self.machine.add_transition(
            trigger="QueryToken",
            source="获取Token",
            dest="创建订单",
            # 获取成功
            conditions=lambda: self.queryTokenCode == 0,
        )
        self.machine.add_transition(
            trigger="QueryToken",
            source="获取Token",
            dest="验证码",
            # 触发验证
            conditions=lambda: self.queryTokenCode == -401,
        )
        self.machine.add_transition(
            trigger="QueryToken",
            source="获取Token",
            dest="获取Token",
            # 获取失败
            conditions=lambda: self.queryTokenCode not in [0, -401],
        )

        # 验证码结束
        self.machine.add_transition(
            trigger="RiskProcess",
            source="验证码",
            dest="获取Token",
            # 验证成功
            conditions=lambda: self.riskProcessCode == 0,
        )
        self.machine.add_transition(
            trigger="RiskProcess",
            source="验证码",
            dest="验证码",
            # 验证失败
            conditions=lambda: self.riskProcessCode != 0,
        )

        # 等待余票结束
        self.machine.add_transition(
            trigger="QueryTicket",
            source="等待余票",
            dest="创建订单",
            # 有票
            conditions=lambda: self.queryTicketCode
            # 超过定时刷新时间
            or not self.data.TimestampCheck(timestamp=self.refreshTime, duration=self.refreshInterval),
        )
        self.machine.add_transition(
            trigger="QueryTicket",
            source="等待余票",
            dest="等待余票",
            # 无票
            conditions=lambda: not self.queryTicketCode,
        )

        # 创建订单结束
        self.machine.add_transition(
            trigger="CreateOrder",
            source="创建订单",
            dest="创建订单状态",
            # 下单成功
            conditions=lambda: self.createOrderCode == 0,
        )
        self.machine.add_transition(
            trigger="CreateOrder",
            source="创建订单",
            dest="获取Token",
            # Token过期
            conditions=lambda: self.createOrderCode in range(100050, 100060),
        )
        self.machine.add_transition(
            trigger="CreateOrder",
            source="创建订单",
            dest="完成",
            # 订单已存在
            conditions=lambda: self.createOrderCode == 100079,
        )
        self.machine.add_transition(
            trigger="CreateOrder",
            source="创建订单",
            dest="创建订单",
            # 失败重试
            conditions=lambda: self.createOrderCode in [429, 100001]
            # 冲刺模式
            or self.data.TimestampCheck(timestamp=self.availableTime, duration=self.availableSchedule[-1][0]),
        )
        self.machine.add_transition(
            trigger="CreateOrder",
            source="创建订单",
            dest="等待余票",
            # 非预定情况
            conditions=lambda: self.createOrderCode not in [0, 100079, 429, 100001, *range(100050, 100060)],
        )

        # 创建订单状态结束
        self.machine.add_transition(
            trigger="CreateStatus",
            source="创建订单状态",
            dest="完成",
            # 锁单成功
            conditions=lambda: self.createStatusCode == 0,
        )
        self.machine.add_transition(
            trigger="CreateStatus",
            source="创建订单状态",
            dest="创建订单",
            # 假单
            conditions=lambda: self.createStatusCode != 0,
        )

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
            self.countdownOver = False
            
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

                elif 60 > countdown > 1:
                    logger.info(f"【等待开票】即将开票! 需要等待 {countdown-1} 秒")
                    sleep(1)
                    countdown -= 1

                # 准点退出循环
                elif countdown < 1:
                    logger.info("【等待开票】即将开票!")
                    sleep(countdown)
                    
                # 预处理
                if countdown == 30:
                    self.api.QueryPrice()
                    logger.info("【等待开票】已缓存商品信息")

        elif countdown == 0:
            logger.info("【等待开票】等待结束! 开始抢票")
            self.countdownOver = True

        else:
            logger.info("【等待开票】已开票! 开始进入抢票模式")
            self.countdownOver = True

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

            # 验证
            case -401:
                logger.warning("【获取Token】需要验证! 下面进入自动过验证")

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
        if not self.queryCache and self.countdownOver:
            self.api.QueryPrice()
            self.queryCache = True
            logger.info("【获取Token】已缓存商品信息")


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
                sleep(self.sleep)

    @logger.catch
    def QueryTicketAction(self) -> None:
        """
        等待余票
        """
        code, msg, clickable, salenum, num = self.api.QueryAmount()
        self.queryTicketCode = clickable or salenum != 4 or num > 0

        match code:
            # 成功
            case 0:
                # 可购
                if self.queryTicketCode:
                    self.availableTime = int(time())
                    match salenum:
                        case 2:
                            logger.warning(f"【等待余票】有票了! 票数:{num}")

                        case 8:
                            logger.info("【等待余票】暂时售罄, 等待放票!")

                        case _:
                            logger.warning(f"【等待余票】可点击状态{clickable} 状态{salenum} 数量{num}, 可下单状态{self.queryTicketCode}")

                # 不可购
                else:
                    logger.info("【等待余票】暂时无票, 持续查询票仓中...")
                    self.availableTime = 0
                    # 刷新
                    sleep(self.sleep)

            # 不知道
            case _:
                logger.error(f"【等待余票】{code}: {msg}")
                # 刷新
                sleep(self.sleep)

    @logger.catch
    def CreateOrderAction(self) -> None:
        """
        创建订单
        """
        logger.info("【创建订单】正在尝试创建订单...")
        self.createOrderCode, msg = self.api.CreateOrder()
        self.refreshTime = int(time())

        match self.createOrderCode:
            # 成功
            case 0:
                logger.success(f"【创建订单】订单创建成功! {msg}")
                self.availableTime = int(time())

            # Token过期
            case x if 100050 <= x <= 100059:
                logger.warning("【创建订单】Token过期! 即将重新获取")

            # 库存不足 219,100009
            case 219 | 100009:
                logger.warning("【创建订单】库存不足!")
                # 刷新
                self.AutoSleepInterval()

            # 请慢一点
            case 100001:
                logger.warning("【创建订单】100001! 服务器卡卡卡咔咔咔咔卡卡卡(无需在意)")
                # 刷新
                self.AutoSleepInterval()

            # 硬控
            case 3:
                logger.error("【创建订单】ERR 3! 请不要开多个脚本给同一实名制购票人(身份证)抢票, 否则会被B站限流")
                # 刷新
                self.AutoSleepInterval()

            # 订单已存在/已购买
            case 100049:
                logger.error("【创建订单】该项目每人限购1张, 已存在购买订单")
                logger.warning("程序正在准备退出...")
                sleep(5)
                sys.exit()

            # 存在未付款订单/有尚未完成订单
            case 100079 | 100048:
                logger.warning("【创建订单】存在冲突订单! 请先支付或取消这一单")
                self.AutoSleepInterval()

            # 超过购买数量
            case 100098:
                logger.error("【创建订单】该票种已超过可购买数量! 请更换账号或票种")
                logger.warning("程序正在准备退出...")
                sleep(5)
                sys.exit()

            # 本项目需要联系人信息
            case 209001:
                logger.error("【创建订单】本项目需要联系人信息! 请补充联系人信息")

            # 项目/票种不可售 等待开票
            case 100016 | 100017:
                logger.error("【创建订单】该项目/票种目前不可售!")
                logger.warning("程序正在准备退出...")
                sleep(5)
                sys.exit()

            # 失败
            case _:
                if msg == "请求错误: 429":
                    logger.warning("【创建订单】429! 服务器卡卡卡咔咔咔咔卡卡卡(无需在意)")
                    self.createOrderCode = 429
                else:
                    logger.error(f"【创建订单】{self.createOrderCode}: {msg}")

                # 刷新
                self.AutoSleepInterval()

    @logger.catch
    def CreateStatusAction(self) -> None:
        """
        创建订单状态
        """
        code, msg = self.api.CreateOrderStatus()
        match code:
            # 正常
            case 0:
                logger.success(f"【创建订单状态】锁单成功! {msg}")

                self.createStatusCode, msg = self.api.GetOrderStatus()
                match self.createStatusCode:
                    # 成功
                    case 0:
                        logger.success("【获取订单状态】订单状态获取成功!")

                    # 不知道
                    case _:
                        logger.error(f"【获取订单状态】{code}: {msg}")
                        # 刷新
                        self.AutoSleepInterval()

            # 不知道
            case _:
                self.createStatusCode = code
                logger.error(f"【创建订单状态】{code}: {msg}")
                # 刷新
                self.AutoSleepInterval()

    @logger.catch
    def FinishAction(self) -> None:
        """
        抢票完成
        """
        url = f"https://show.bilibili.com/platform/orderDetail.html?order_id={self.api.orderId}"
        notice = Notice(title="抢票", message=f"下单成功! 请在十分钟内支付, 链接:{url}")
        logger.success(f"【完成】下单成功! 请在十分钟内支付, 链接:{url}")
        webbrowser.open(url)

        # 通知
        noticeThread = []
        t1 = threading.Thread(target=notice.Message)
        t2 = threading.Thread(target=notice.Sound)
        t3 = threading.Thread(target=notice.PushPlus, args=(self.notice["pushplus"],))
        t4 = threading.Thread(target=notice.Ding, args=(self.notice["dingding"],))
        t5 = threading.Thread(target=notice.WX, args=(self.notice["wx"],))
        t6 = threading.Thread(target=notice.FTQQ, args=(self.notice["ftqq"],))
        t7 = threading.Thread(target=notice.Bark, args=(self.notice["bark"],))
        t8 = threading.Thread(target=notice.Mail, args=(self.notice["smtp"],))

        if self.notice["system"]:
            noticeThread.append(t1)
        if self.notice["sound"]:
            noticeThread.append(t2)

        if len(self.notice["pushplus"]) > 0:
            noticeThread.append(t3)
        if len(self.notice["dingding"]) > 0:
            noticeThread.append(t4)
        if len(self.notice["wx"]) > 0:
            noticeThread.append(t5)
        if len(self.notice["ftqq"]) > 0:
            noticeThread.append(t6)
        if len(self.notice["bark"]) > 0:
            noticeThread.append(t7)
        if len(self.notice["smtp"]["mail_host"]) > 0:
            noticeThread.append(t8)

        for t in noticeThread:
            t.start()

    @logger.catch
    def AutoSleepInterval(self) -> None:
        """
        自动Sleep策略
        """
        # 票仓有票时
        if self.data.TimestampCheck(timestamp=self.availableTime, duration=self.availableSchedule[-1][0]):
            for i in range(len(self.availableSchedule) - 1):
                start = self.availableSchedule[i][0]
                end = self.availableSchedule[i + 1][0]
                # 超过start, 未满足end
                if not self.data.TimestampCheck(timestamp=self.availableTime, duration=start) and self.data.TimestampCheck(timestamp=self.availableTime, duration=end):
                    sleepTime = self.availableSchedule[i + 1][1]
                    break

            logger.info(f"【创建订单】出票期, 请求间隔将自动调整至{sleepTime:.2f}秒")
            sleep(sleepTime)

        # 常规试探
        else:
            sleep(self.sleep)

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
        try:
            while self.state != "完成":
                self.trigger(job[self.state])
            return True

        except KeyboardInterrupt:
            logger.error("【状态机】任务被中断!")

            # 状态机状态网页显示体验
            # self.machine.stop_server()
            return False
