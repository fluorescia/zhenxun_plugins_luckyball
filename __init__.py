from nonebot.adapters.onebot.v11 import GroupMessageEvent, Message, Bot, GROUP
from nonebot.adapters.onebot.v11 import  GroupMessageEvent  , Message
from nonebot import on_command, get_bot, get_driver, logger
from nonebot.adapters.onebot.v11.permission import GROUP
from nonebot.params import CommandArg
from nonebot.matcher import Matcher
from nonebot.permission import SUPERUSER
from models.bag_user import BagUser
from utils.utils import scheduler, is_number
from services.log import logger
from models.group_member_info import GroupInfoUser
import re
from pathlib import Path
import random
from .model import lottery,lottery_group


__zx_plugin_name__ = "幸运球"
__plugin_usage__ = """
usage：
    玩家花费金币购买一个号数，每天固定一个时间开奖。
    如果中奖，奖励为所有人花费总额加上基础奖池后减去税
    若无人获奖，累计到下一次
    开奖后清空玩家号码并重置奖池
    指令：
        祈祷数字[num]
        #数据查看：
            我的幸运球
            群幸运球统计
        # 超级用户指令：
            手动开启幸运球
            定时幸运球 状态|设置?:?|禁用|花费|范围|奖池|税
    举例：
        祈祷数字23
        我的幸运球
        群幸运球统计
        #以下是超级用户指令
        定时幸运球状态
        定时幸运球设置18:00
        定时幸运球禁用
        定时幸运球花费300 
        定时幸运球范围50 #注意这里代表设置范围是1-50
        定时幸运球奖池1000 #用于设置中奖后重置奖池的基础金币,设置为-1则使用默认值(单次花费*号码范围)
        定时幸运球税30 #如果有人中奖，那么将会被拿走30%的奖励

""".strip()
__plugin_des__ = "另一种形式的刮刮乐（"
__plugin_type__ = ("群内小游戏",)
__plugin_cmd__ = [
    "祈祷数字",
    "我的幸运球",
    "群幸运球统计"
]
__plugin_version__ = 0.1
__plugin_author__ = "fluoresce"
__plugin_settings__ = {
    "level": 5,
    "default_status": True,
    "limit_superuser": False,
    "cmd": ["祈祷数字","我的幸运球","群幸运球统计"],
}






kj_matcher = on_command("定时幸运球", aliases={"开球时间"}, priority=5, permission=SUPERUSER, block=True)
shoudong = on_command("手动开启幸运球", priority=5, permission=SUPERUSER, block=True)
buyltnum = on_command("祈祷数字", priority=5,permission=GROUP, block=True) 
record = on_command("我的幸运球", priority=5,permission=GROUP, block=True) 
record2 = on_command("群幸运球统计", priority=5,permission=GROUP, block=True) 
#↓设置每日自动开奖功能
#搬运的Akirami摸鱼日历代码
try:
    import ujson as json
except ModuleNotFoundError:
    import json


#打开json
subscribe = Path(__file__).parent / "subscribe.json"
subscribe_list = json.loads(subscribe.read_text("utf-8")) if subscribe.is_file() else {}
def save_subscribe():
    subscribe.write_text(json.dumps(subscribe_list, indent = 4, ensure_ascii = False), encoding="utf-8")


#定时任务相关
driver = get_driver()
@driver.on_startup
async def subscribe_jobs():
    for group_id, info in subscribe_list.items():
        try:
            scheduler.add_job(
                push_calendar,
                "cron",
                args=[group_id],
                id=f"lottery_calendar_{group_id}",
                replace_existing=True,
                hour=info["hour"],
                minute=info["minute"],
            )
        except KeyError:
            pass

async def push_calendar(group_id: str):
    bot = get_bot()
    pst = await kaijiang(int(group_id))
    logger.info(f"自动开奖成功")
    await bot.send_group_msg(group_id=int(group_id), message=pst)

def calendar_subscribe(group_id: str, hour: str, minute: str) -> None:
    try:
        subscribe_list[group_id]["hour"] = hour
        subscribe_list[group_id]["minute"] = minute
    except KeyError:
        subscribe_list[group_id] = {"hour":hour,"minute":minute}
    save_subscribe()
    scheduler.add_job(
        push_calendar,
        "cron",
        args=[group_id],
        id=f"lottery_calendar_{group_id}",
        replace_existing=True,
        hour=hour,
        minute=minute,
    )
    logger.debug(f"群[{group_id}]设置每日开奖时间为：{hour}:{minute}")


#用于指令设置幸运球的各参数
@kj_matcher.handle()
async def kjtime(
    event: GroupMessageEvent, matcher: Matcher, args: Message = CommandArg()
):
    if cmdarg := args.extract_plain_text():
        if "状态" in cmdarg:
            push_state = scheduler.get_job(f"lottery_calendar_{event.group_id}")
            moyu_state = "每日幸运球状态：\n每日幸运球: " + ("已开启" if push_state else "已关闭")
            if push_state:
                group_id_info = subscribe_list[str(event.group_id)]
                moyu_state += (
                    f"\n幸运球时间: {group_id_info['hour']}:{group_id_info['minute']}"
                )
                try:
                    moyu_state += f"\n花费金币:{group_id_info['gold']}"
                except KeyError:
                    moyu_state += "\n花费金币:200(默认)"

                try:
                    moyu_state += f"\n祈祷范围:1-{group_id_info['num']}"
                except KeyError:
                    moyu_state += "\n祈祷范围:1-30(默认)"

                try:
                    moyu_state += f"\n基础奖池:{group_id_info['pool']}"
                except KeyError:
                    moyu_state += "\n基础奖池:范围*花费(默认)"

                try:
                    moyu_state += f"\ntax:{group_id_info['tax']}%"
                except KeyError:
                    moyu_state += "\ntax:30%(默认)"                

            await matcher.finish(moyu_state)

        elif "设置" in cmdarg:
            if ":" in cmdarg or "：" in cmdarg:
                match = re.search(r"(\d*)[:：](\d*)", cmdarg)
                if match and match[1] and match[2]:
                    calendar_subscribe(str(event.group_id), match[1], match[2])
                    await kj_matcher.finish(f"每日幸运球的时间已设置为：{match[1]}:{match[2]}")
                else:
                    await kj_matcher.finish("设置时间失败，请输入正确的格式，格式为：定时幸运球设置[小时]:[分钟]")
            else:
                await kj_matcher.finish("设置时间失败，请输入正确的格式，定时幸运球设置[小时]:[分钟]")

        elif "花费" in cmdarg:
            match = re.search(r"-?[1-9]\d*", cmdarg)
            if match[0]:
                try:
                    subscribe_list[str(event.group_id)]["gold"] = match[0]
                except KeyError:
                    subscribe_list[str(event.group_id)] = {"gold":match[0]}
                save_subscribe()
                await kj_matcher.finish(f"每人幸运球的花费已设置为：{match[0]}金币")
            else:
                await kj_matcher.finish("设置花费失败，请输入正确的格式，格式为：定时幸运球花费[金币]")
        
        elif "范围" in cmdarg:
            match = re.search(r"-?[1-9]\d*", cmdarg)
            if int(match[0])>1:
                try:
                    subscribe_list[str(event.group_id)]["num"] = match[0]
                except KeyError:
                    subscribe_list[str(event.group_id)] = {"num":match[0]}
                save_subscribe()
                await kj_matcher.finish(f"每日幸运球的范围已设置为：1-{match[0]}")
            else:
                await kj_matcher.finish("设置范围失败，请输入正确的格式，格式为：定时幸运球范围[最大数字]")

        elif "奖池" in cmdarg:
            match = re.search(r"-?[1-9]\d*", cmdarg)
            if int(match[0]) > -2:
                try:
                    subscribe_list[str(event.group_id)]["pool"] = match[0]
                except KeyError:
                    subscribe_list[str(event.group_id)] = {"pool":match[0]}
                save_subscribe()
                await kj_matcher.finish(f"每日幸运球的中奖后重置奖池金币设置为：{match[0]}")
            else:
                await kj_matcher.finish("设置基础奖池失败，请输入正确的格式，格式为：定时幸运球奖池[数字]")

        elif "税" in cmdarg:
            match = re.search(r"-?[1-9]\d*", cmdarg)
            if int(match[0]) > 0 and int(match[0]) < 100:
                try:
                    subscribe_list[str(event.group_id)]["tax"] = match[0]
                except KeyError:
                    subscribe_list[str(event.group_id)] = {"tax":match[0]}
                save_subscribe()
                await kj_matcher.finish(f"每日幸运球tax设置为：{match[0]}")
            else:
                await kj_matcher.finish("设置tax失败，请输入正确的格式，格式为：定时幸运球税[百分之多少]")
    
        elif "禁用" in cmdarg or "关闭" in cmdarg:
            del subscribe_list[str(event.group_id)]
            save_subscribe()
            scheduler.remove_job(f"lottery_calendar_{event.group_id}")
            await matcher.finish("每日幸运球已禁用")

        else:
            await matcher.finish("修改幸运球的参数不正确")
#↑

#购买彩票         
@buyltnum.handle()
async def _(event: GroupMessageEvent, arg: Message = CommandArg()):
    msg = arg.extract_plain_text().strip()
    user = await lottery.ensure(event.user_id, event.group_id)

    if user.numberlt > 0:
        await buyltnum.finish(f"你今天已经祈祷过了，数字是{user.numberlt}")
    
    #获取购买最大号码，若未定义则设置为默认的30
    try:
        kjnum_max = subscribe_list[str(event.group_id)]["num"]
    except KeyError:
        kjnum_max = 30
    
    #获取一次花费的金币，若未定义则设置为默认的200
    try:
        oneltcost = int(subscribe_list[str(event.group_id)]["gold"])
    except KeyError:
        oneltcost = 200
    
    if is_number(msg):
        num = int(msg)
        if num < 1 or num > int(kjnum_max):     
            await buyltnum.finish(f"请输入1-{kjnum_max}的数字")
            
        uid = event.user_id
        group = event.group_id
        gold = await BagUser.get_gold(uid, group)
        
        if gold >= oneltcost:
            await BagUser.spend_gold(uid, group, oneltcost)
            await lottery.addltnum(uid, group, num, oneltcost)              #写入玩家购买的号码，玩家加祈祷数+1,增加玩家累计消费
            await lottery_group.caipiaoleijiadd(group,oneltcost)             #增加群累计奖金池，群当日祈祷人数+1，群总祈祷次数+1
            groupe = await lottery_group.ensure_group(group)
            await buyltnum.finish(f"恭喜你使用{oneltcost}金币祈祷了数字{num},当前群积累的奖励：{groupe.caipiaoleiji}")
        else:
            await buyltnum.finish("你的钱好像不够诶")
    else:
        await buyltnum.finish(f"号码只能是数字")

#手动开奖
@shoudong.handle()
async def _(bot: Bot, event: GroupMessageEvent):
    pst = await kaijiang(event.group_id)
    logger.info(f"手动开奖成功")
    await shoudong.finish(f"{pst}")

#开奖函数
async def kaijiang(groupid):
    #获取购买最大号码，若未定义则设置为默认的30
    try:
        kjnum_max = int(subscribe_list[str(groupid)]["num"])
    except KeyError:
        kjnum_max = 30

    #出开奖号码
    winnumber = random.randint(1, kjnum_max)

    #计算中奖人名单
    win_list = []
    try:
        user_list = await lottery.get_all_users(groupid)     
        for user in user_list:
            if user.numberlt > 0:
                if user.numberlt == winnumber:
                    win_list.append(user.user_qq)
    except:
        logger.error("开奖错误")

    group_ensure = await lottery_group.ensure_group(groupid)              #获取幸运球群组信息

    winplayernum = 	len(win_list)                                         #中奖人数
    ptin = group_ensure.groupdaydonum                                     #参与人数
    total_gold = group_ensure.caipiaoleiji                                #今日奖励
    
    if winplayernum > 0:
        ##结算
        #获取一次花费的金币，若未定义则设置为默认的200
        try:
            oneltcost = int(subscribe_list[str(groupid)]["gold"])
        except KeyError:
            oneltcost = 200
        #获取基础奖池设置,若未设置则使用范围*花费
        try:
            poolgold = int(subscribe_list[str(groupid)]["pool"])
            if poolgold == -1:
                poolgold = oneltcost*kjnum_max
        except KeyError:
            poolgold = oneltcost*kjnum_max
        #获取税收参数,若未设置则使用默认值30
        try:
            goldtax = int(subscribe_list[str(groupid)]["tax"])/100
        except KeyError:
            goldtax = 0.3

        total_gold = (1-goldtax)*total_gold                                     #收税后总奖励金币
        strpost = f"今日幸运号码是:{winnumber}，祈祷人数：{ptin}\n幸运者："
        getgold = int(total_gold/winplayernum)                                  #每个中奖者能得金币
        for x in win_list:
            await BagUser.add_gold(x, groupid,getgold)
            await lottery.windataup(x,groupid,getgold)
                     
            niname = (await GroupInfoUser.get_member_info(x, groupid)).user_name
            strpost += f'{niname}、'
        
        await lottery_group.caipiaoleijiset(groupid, poolgold)                         #清空奖池
        
        strpost = strpost[:-1] + f"。每人获得{getgold}枚金币。"   
    else:
        strpost = f"今天的幸运数字是：{winnumber}。祈祷人数：{ptin}。\n没有人好运呢，奖励累计到下一天。当前累计金币：{total_gold}"

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

#数据查看
@record.handle()
async def _(event: GroupMessageEvent):
    user = await lottery.ensure(event.user_id, event.group_id)
    groupe = await lottery_group.ensure_group(event.group_id)
    await record.send(
        f"幸运球\n"
        f"祈祷次数：{user.dotimes}\n"
        f"幸运次数：{user.wintimes}\n"
        f"花费总额：{user.userallcost}\n"
        f"获得总额：{user.winmoney}\n"
        f"当前群积累的奖励：{groupe.caipiaoleiji}",
        at_sender=True,
    )

@record2.handle()
async def _(event: GroupMessageEvent):
    groupe = await lottery_group.ensure_group(event.group_id)
    await record2.send(
        f'群幸运球统计\n'
        f'今日祈祷人数：{groupe.groupdaydonum}\n'
        f'群总祈祷次数：{groupe.groupalldonum}\n'
        f'群总幸运人次：{groupe.groupwintime}'
    )

