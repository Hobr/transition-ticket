import smtplib
import requests,json,re
from loguru import logger
#from i18n import *
#from globals import load_config



class PUSH():
    def __init__(self,config):
        self.config = config
        self.title="BTP有新推送消息"
        self.headers = {
        "Content-Type": "application/json",
        "Charset": "UTF-8"
         }
        #dingding
        try:
         self.dingding_token=config['dingding_token']
        except:
            logger.error("dingding_not_set")
            #logger.error(i18n_format("webhook_not_set"))
            self.dingding_token=''
        #push_plus
        try:
            self.pushplus_token=config['pushplus_token']
        except:
            logger.error("pushplus_not_set")
            #logger.error(i18n_format("pushplus_not_set"))
            self.pushplus_token=''
        #smtp
        try:
            self.smtp_mail_host=config['smtp_mail_host']
            self.smtp_mail_user=config['smtp_mail_user']
            self.smtp_mail_pass=config['smtp_mail_pass']
            self.smtp_sender=config['smtp_sender']
            self.smtp_receivers=config['smtp_receivers']
        except:
            logger.error("smtp_not_set")
            #logger.error(i18n_format("smtp_not_set"))
            self.smtp_mail_host=""
            self.smtp_mail_user=""
            self.smtp_mail_pass=""
            self.smtp_sender=""
            self.smtp_receivers=['']
        #bark
        try:
            self.bark_token=config['bark_token']
        except:
            logger.error("bark_not_set")
            #logger.error(i18n_format("bark_not_set"))
            self.bark_token=""
        #ftqq
        try:
            self.ftqq_token=config['ftqq_token']
        except:
            logger.error("ftqq_not_set")
            #logger.error(i18n_format("ftqq_not_set"))
            self.ftqq_token=""
        #wx
        try:
            self.wx_token=config['wx_token']
        except:
            logger.error("webhook_not_set")
            #logger.error(i18n_format("wx_not_set"))
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
        info = requests.post(url, data=message_json, headers=self.headers)
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
        info=requests.post(url, json=data,headers=self.headers)
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
         info=requests.post(url, data=data,headers=self.headers)
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
            info=requests.post(url, json=data,headers=self.headers)
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
            logger.info("send_success")
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
          info=requests.post(url,json=data)
          logger.info("bark_send_success")
          logger.debug(info.text)
          #logger.info(i18n_format("bark_send_success"))
        except Exception as e:
          logger.error(e)

if __name__ == "__main__":
    config={}
    #只需要填入token即可，不要全部链接
    config['dingding_token']=""
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