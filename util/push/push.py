import smtplib
import json
from loguru import logger
from util.Request import Request
#from i18n import *




class PUSH():
    def __init__(self,config):
        self.config = config
        self.title="BTP有新推送消息"
        self.net = Request()
        self.headers = {
        "Content-Type": "application/json",
        "Charset": "UTF-8"
         }
        if 'dingding_token' in config:
            self.dingding_token=config['dingding_token']
        else:
            self.dingding_token=''
        if 'pushplus_token' in config:
            self.pushplus_token=config['pushplus_token']
        else:
            self.pushplus_token=''
        if 'smtp_mail_host' in config:
            self.smtp_mail_host=config['smtp_mail_host']
        else:
            self.smtp_mail_host=""
        if 'smtp_mail_user' in config:
            self.smtp_mail_user=config['smtp_mail_user']
        else:
            self.smtp_mail_user=""
        if 'smtp_mail_pass' in config:
            self.smtp_mail_pass=config['smtp_mail_pass']
        else:
            self.smtp_mail_pass=""
        if 'smtp_sender' in config:
            self.smtp_sender=config['smtp_sender']
        else:
            self.smtp_sender=""
        if 'smtp_receivers' in config:
            self.smtp_receivers=config['smtp_receivers']
        else:
            self.smtp_receivers=['']
        if 'bark_token' in config:
            self.bark_token=config['bark_token']
        else:
            self.bark_token=""
        if 'ftqq_token' in config:
            self.ftqq_token=config['ftqq_token']
        else:
            self.ftqq_token=""
        if 'wx_token' in config:
            self.wx_token=config['wx_token']
        else:
            self.wx_token=""
        
                  
    def push(self,message):
        self.message = message
        if self.dingding_token!='':
            self.ding_push()
        if self.pushplus_token!='':
            self.pushplus()
        if self.bark_token!='':
            self.bark() 
        if self.smtp_mail_host and self.smtp_mail_pass and self.smtp_sender and self.smtp_receivers: 
            self.smtp()
        if self.ftqq_token:
            self.ftqq()
        if self.wx_token:
            self.wx_push()  

    def ding_push(self):
        url=f"https://oapi.dingtalk.com/robot/send?access_token={self.dingding_token}"
        # 构建请求数据
        msg = {
        "msgtype": "text",
        "text": {
            "content": self.message
        },
        "at": {
            "isAtAll": False
        }
        }
        # 对请求的数据进行json封装
        message_json = json.dumps(msg)
        # 发送请求
        info = self.net.Response(method='post',url=url, params=message_json,isJson=True)
        # 打印返回的结果
        logger.info(info.text)
        
    def pushplus(self):
       
      
      token = self.pushplus_token #在pushpush网站中可以找到
      
      url = 'http://www.pushplus.plus/send'
      data = {
        "token":token,
        "title":self.message,
        "content":self.message
      }
      
      try:
        info=self.net.Response(method='post',url=url, params=data,isJson=True)
        logger.debug(info.text)
        #logger.info(i18n_format("pushplus_send_success"))
        logger.info("pushplus_send_success")
      except Exception as e:
        logger.error(e)
      
    def ftqq(self):
        data={
            "title":self.title,
            "desp":self.message,
            "noip":1
        }
        url=f"https://sctapi.ftqq.com/{self.ftqq_token}.send"
        try:
         info=self.net.Response(method='post',url=url, params=data,isJson=True)
         logger.debug(info.text)
         #logger.info(i18n_format("bark_send_success"))
         logger.info("bark_send_success")
        except Exception as e:
            logger.error(e)
        


    def wx_push(self):
        url = f'https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key={self.wx_token}'
        data = {
          'msgtype': 'text',
          'text': {
              'content': self.message
             }
          }
        try:
            info=self.net.Response(method='post',url=url, params=data,isJson=True)
            logger.debug(info.text)
            #logger.info(i18n_format("wx_send_success"))
            logger.info("wx_send_success")
        except Exception as e:
            logger.error(e)
        


    def smtp(self):
        from email.mime.text import MIMEText
        #设置服务器所需信息
        #163邮箱服务器地址
        mail_host = self.smtp_mail_host 
        #163用户名
        mail_user = self.smtp_mail_user  
        #密码(部分邮箱为授权码) 
        mail_pass = self.smtp_mail_pass   
        #邮件发送方邮箱地址
        sender = self.smtp_sender  
        #邮件接受方邮箱地址，注意需要[]包裹，这意味`着你可以写多个邮件地址群发
        receivers = self.smtp_receivers  

        #设置email信息
        #邮件内容设置
        message = MIMEText(self.message,'plain','utf-8')
        #邮件主题       
        message['Subject'] = self.title 
        #发送方信息
        message['From'] = sender 
        #接受方信息 
        for receiver in receivers:
          message['To'] = receiver    
        

          #登录并发送邮件
          try:
            smtpObj = smtplib.SMTP() 
            #连接到服务器
            smtpObj.connect(mail_host,25)
            #登录到服务器
            smtpObj.login(mail_user,mail_pass) 
            #发送
            smtpObj.sendmail(
                sender,receivers,message.as_string()) 
            #退出
            smtpObj.quit() 
            #logger.info(i18n_format("send_success"))
            logger.info("smtp_send_success")
          except smtplib.SMTPException as e:
            logger.error(e) #打印错误
            
        
    def bark(self):
        data={
            "title":self.title,
            "body":self.message,
            "level":"timeSensitive",
            #推送中断级别。 
#active：默认值，系统会立即亮屏显示通知
#timeSensitive：时效性通知，可在专注状态下显示通知。
#passive：仅将通知添加到通知列表，不会亮屏提醒。"""   
            "badge":1,
            "icon":"https://ys.mihoyo.com/main/favicon.ico",
            "group":"BHYG", 
            "isArchive":1
        }
        url=f'https://api.day.app/{self.bark_token}'
        try:
          info=self.net.Response(method='post',url=url, params=data,isJson=True)
          logger.info("bark_send_success")
          logger.debug(info.text)
          #logger.info(i18n_format("bark_send_success"))
        except Exception as e:
          logger.error(e)

if __name__ == "__main__":
    config={}
    #只需要填入token即可，不要全部链接
    config['dingding_token']="123456"
    config['wx_token']=''
    config['pushplus_token']=''
    config['bark_token']=""  
    config['smtp_mail_host']='' 
    config['smtp_mail_user']='' 
    config['smtp_mail_pass']='' 
    config['smtp_sender']=''
    config['smtp_receivers']=['']  #可群发
    config['ftqq_token']=''
    push_self=PUSH(config)  #传config创建对象
    PUSH.push(push_self,"test")  #以后每次调用就可以了
    PUSH.push(push_self,"test2")