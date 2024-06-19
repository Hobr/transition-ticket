# B站会员购 蹲票脚本

## 声明

[电报交流群](https://t.me/bilibili_ticket)

本程序仅供学习交流, 不得用于商业用途,

使用本程序进行违法操作产生的法律责任由操作者自行承担,

对本程序进行二次开发/分发时请注意遵守GPL-3.0开源协议,

本脚本仅适用于蹲回流票, 我们反对将其用于抢票.

## 使用

注意:

1. 现仅支持部分活动, 主要是类似于BW2024这样的*实名制 一人一票 无选座*活动, 后期会增加更多类型的票务支持;
2. 如使用浏览器登录功能, 您的电脑里必须安装Chrome/Edge/Firefox浏览器, 如有安装还是提供无法启动, 则需要自行安装其中一个浏览器的Web Driver.

```bash
pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple
pip install poetry virtualenv

virtualenv venv
source venv/script/activate
poetry install
python cli.py
```

## 运行流程

![FSM](assest/fsm.png)

## 开发计划

- 1.0.0 Release (BW开票前)
  - [ ] 抢票流程细节补充/修复
  - [ ] Header补充
  - [ ] PyInstaller打包
  - [ ] 删除Debug输出、无用日志、未开发功能、未用到的Class、未用到的依赖
  - [ ] GitHub Action打包

- 1.1.0 (BW开票期间)
  - [ ] 命令行账号密码/短信验证登录
  - [ ] 账号密码登录 二次手机验证码
  - [ ] 手机验证码登录
  - [ ] 文档

- 1.2.0
  - [ ] 解析JS + biliTicker_gt
  - [ ] 刷新Cookie
  - [ ] 手动验证

- 1.3.0
  - [ ] 多种类型活动抢票
  - [ ] 图形界面(PySide6)

- 1.4.0
  - [ ] 注销Cookie
  - [ ] Docker(Headless)

- 1.5.0
  - [ ] 网页界面(Gradio)

## 开发

- Python >=3.10,<3.13

```bash
pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple
pip install poetry virtualenv

virtualenv venv
source venv/script/activate
poetry install --with dev
pre-commit install

# 更新
poetry update --sync
pre-commit autoupdate
```

### 同步到公开仓库

```bash
git remote add bilibili-ticket git@github.com:bilibili-ticket/bilibili-ticket-python.git

git config user.name "bilibili-ticket"
git config user.email "<>"
git config commit.gpgsign false

git checkout --orphan version
git add -A
git commit -am "Initial commit"
git push -u bilibili-ticket version
```
