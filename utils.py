from models.bag_user import BagUser
from models.group_member_info import GroupInfoUser
from configs.config import Config
from services.log import logger

import random
from .model import lottery,lottery_group

async def kaijiang(groupid):
    kjnum_max = Config.get_config("luckyball", "KJNUM_MAX")

    #出开奖号码，计算$中奖人数$总参与人数
    winnumber = random.randint(1, kjnum_max)
    
    win_list = []
    #计算中奖人名单
    try:
        user_list = await lottery.get_all_users(groupid)     
        for user in user_list:
            if user.numberlt > 0:
                if user.numberlt == winnumber:
                    win_list.append(user.user_qq)
    except:
        logger.error("开奖错误")

    group_ensure = await lottery_group.ensure_group(groupid)

    winplayernum = 	len(win_list)                                         #中奖人数
    ptin = group_ensure.groupdaydonum                                     #参与人数
    total_gold = group_ensure.caipiaoleiji                                #今日奖励
    strpost = f"今日幸运号码是:{winnumber}，祈祷人数：{ptin}\n幸运者："
    if winplayernum > 0:
        #结算
        getgold = int(total_gold/winplayernum)                                  #每个中奖者能得金币
        for x in win_list:
            await BagUser.add_gold(x, groupid,getgold)
            await lottery.windataup(x,groupid,getgold)
                     
            niname = (await GroupInfoUser.get_member_info(x, groupid)).user_name
            strpost += f'{niname}、'
        await lottery_group.caipiaoleijiset(groupid, 0)                         #清空奖池
        
        strpost = strpost[:-1] + f"。每人获得{getgold}枚金币"   
    else:
        strpost = f"今天的幸运数字是：{winnumber}。没有人好运呢，奖励累计到下一天。当前累计金币：{total_gold}"

    #重置玩家购买号数，清空lottery_group的当日祈祷人数
    try:
        user_list2 = await lottery.get_all_users(groupid)
        for user in user_list2:
            await user.update(numberlt=0).apply()
        logger.info(f"重置群成员每日购买号数成功")
        await lottery_group.caipiao_update(groupid,winplayernum)                #增加群累计中奖人数，清空群每日祈祷人数
        logger.info(f"重置群每日祈祷人数成功")
    except Exception as e:
        logger.error(f"重置每日购买彩票错误 e:{e}")
    return strpost