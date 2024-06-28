import glob
import sys
from os import getcwd, makedirs, path
from time import sleep

import yaml
from loguru import logger

from util.Data import Data


class Config:
    """
    配置
    """

    @logger.catch
    def __init__(self, dir: str):
        """
        初始化

        dir: 目录
        """
        self.rootDir = getcwd()
        self.dir = path.join(self.rootDir, f"config/{dir}")

    @staticmethod
    def dict_to_yaml_str(data: dict) -> str:
        """
        将dict转换为YAML格式的str
        """
        return yaml.dump(data, default_flow_style=False)

    @staticmethod
    def yaml_str_to_dict(yaml_str: str) -> dict:
        """
        将YAML格式的str转换为dict
        """
        return yaml.safe_load(yaml_str)

    @logger.catch
    def List(self) -> list:
        """
        列表
        """
        try:
            if not path.exists(self.dir):
                makedirs(self.dir)

            files = glob.glob(path.join(self.dir, "*.yaml"))
            files = [path.splitext(path.basename(file))[0] for file in files]
            return files

        except Exception as e:
            logger.exception(f"【配置】读取配置列表错误! {e}")
            logger.warning("程序正在准备退出...")
            sleep(5)
            sys.exit()

    @logger.catch
    def Load(self, filename: str, decrypt: bool = False) -> dict:
        """
        读取

        decrypt: 是否解密
        """
        try:
            with open(f"{self.dir}/{filename}.yaml", encoding="utf-8") as file:
                if decrypt:
                    yaml_str = file.read()
                    decrypted_yaml_str = Data().AESDecrypt(yaml_str)
                    return self.yaml_str_to_dict(decrypted_yaml_str)
                else:
                    return yaml.safe_load(file)

        except FileNotFoundError:
            logger.exception(f"【配置】读取的配置文件 {filename} 不存在!")
            return {}

        except yaml.YAMLError as e:
            logger.exception(f"【配置】读取配置文件错误!{e}")
            return {}

    @logger.catch
    def Save(self, filename: str, data: dict, encrypt: bool = False) -> None:
        """
        写入并加密

        data: 数据
        encrypt: 是否加密
        """
        try:
            with open(f"{self.dir}/{filename}.yaml", "w", encoding="utf-8") as file:
                if encrypt:
                    yaml_str = self.dict_to_yaml_str(data)
                    encrypted_yaml_str = Data().AESEncrypt(yaml_str)
                    file.write(encrypted_yaml_str)
                else:
                    yaml.dump(data, file, allow_unicode=True)

        except Exception as e:
            logger.exception(f"【配置】保存配置文件错误!{e}")
