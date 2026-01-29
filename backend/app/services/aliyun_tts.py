import json
import logging
import time
from typing import Optional
from aliyunsdkcore.client import AcsClient
from aliyunsdkcore.request import CommonRequest
from ..config import settings
import httpx

logger = logging.getLogger(__name__)

class AliyunTTSService:
    _token = None
    _token_expire_time = 0

    @classmethod
    def get_token(cls) -> Optional[str]:
        """
        获取阿里云NLS访问令牌 (缓存有效)
        """
        # 如果当前token有效且距离过期还有10分钟以上，直接返回
        if cls._token and time.time() < cls._token_expire_time - 600:
            return cls._token

        try:
            # 创建AcsClient实例
            client = AcsClient(
                settings.ALIYUN_ACCESS_KEY_ID,
                settings.ALIYUN_ACCESS_KEY_SECRET,
                "cn-shanghai"
            )

            # 创建request，设置参数
            request = CommonRequest()
            request.set_method('POST')
            request.set_domain('nls-meta.cn-shanghai.aliyuncs.com')
            request.set_version('2019-02-28')
            request.set_action_name('CreateToken')

            response = client.do_action_with_exception(request)
            response_json = json.loads(response)

            if 'Token' in response_json:
                token = response_json['Token']
                cls._token = token['Id']
                cls._token_expire_time = token['ExpireTime']
                logger.info(f"Successfully obtained NLS Token, expires at {cls._token_expire_time}")
                return cls._token
            else:
                logger.error(f"Failed to get NLS Token: {response_json}")
                return None

        except Exception as e:
            logger.error(f"Error getting NLS Token: {e}")
            return None

    @classmethod
    async def synthesize(cls, text: str) -> Optional[bytes]:
        """
        调用阿里云RESTful API进行语音合成
        """
        token = cls.get_token()
        if not token:
            logger.error("Cannot synthesize: Token is missing")
            return None

        url = "https://nls-gateway-cn-shanghai.aliyuncs.com/stream/v1/tts"
        
        # 语音合成参数配置
        # 参考文档: https://help.aliyun.com/document_detail/94736.html
        payload = {
            "appkey": settings.ALIYUN_NLS_APP_KEY,
            "token": token,
            "text": text,
            "format": "mp3",
            "sample_rate": 16000,
            # "voice": "zhiqi_emo", # 默认知琪，或者其他萌妹音，如 "siqi", "aitong"
            # 既然用户要萌妹音，我们选一个比较甜美的，或者使用默认的
            # "voice": "aitong" # 艾彤：儿童音，可能比较萌
            # "voice": "zhiqi" # 温柔女声
            # "voice": "nvsheng" # 标准女声
            # "voice": "zhiqi", # 暂时使用知琪，比较通用且好听，或者用户指定
            # "voice": "aitong", # 艾彤：儿童音，可爱小朋友的声音
            # "voice": "zhiqi", # 知琪：温柔女声，比较中性
            "voice": "jielidou", # 杰力豆：治愈童声
            "volume": 50,
            "speech_rate": 0, # 语速 0
            "pitch_rate": 0 # 语调 0
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=payload, timeout=10.0)
                
                if response.status_code == 200:
                    content_type = response.headers.get("Content-Type", "")
                    if "audio" in content_type:
                        return response.content
                    else:
                        logger.error(f"TTS API returned non-audio: {response.text}")
                        return None
                else:
                    logger.error(f"TTS API Error {response.status_code}: {response.text}")
                    return None
        except Exception as e:
            logger.error(f"TTS Request Exception: {e}")
            return None
