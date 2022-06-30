from nonebot.adapters.onebot.v11 import GroupMessageEvent, Message, Bot, GROUP
from nonebot.adapters.onebot.v11 import  GroupMessageEvent  , Message
from nonebot import on_command, get_bot, get_driver, logger
from nonebot.adapters.onebot.v11.permission import GROUP
from nonebot.params import CommandArg, Arg
from nonebot.matcher import Matcher
from nonebot.permission import SUPERUSER
from nonebot.typing import T_State

from models.bag_user import BagUser
from configs.config import Config
from utils.utils import scheduler
from services.log import logger

import re
from pathlib import Path

from .model import lottery,lottery_group
from .utils import kaijiang

kjnum_max = Config.get_config("luckyball", "KJNUM_MAX")
oneltcost = Config.get_config("luckyball", "ONELTCOST")



__zx_plugin_name__ = "幸运球"
__plugin_usage__ = f"""
usage：
    玩家花费{oneltcost}购买一个号数，每天固定一个时间开奖。
    奖励为所有人花费总额，若无人获奖累计到下一次
    开奖后清空玩家号码
    指令：
        祈祷数字[1-{kjnum_max}]
        #数据查看：
            我的幸运球
            群幸运球统计
        # 超级用户指令：
            手动开启幸运球
            定时幸运球 状态|设置?:?|禁用
    举例：
        祈祷数字23
        我的幸运球
        定时幸运球状态
        定时幸运球设置18:00
""".strip()
__plugin_des__ = "另一种形式的刮刮乐（"
__plugin_type__ = ("金币相关",)
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

__plugin_configs__ = {
    "ONELTCOST": {
        "value": 200, 
        "help": "买一次花费的金币", 
        "default_value": 200
    },
    "KJNUM_MAX": {
        "value": 30,
        "help": "限制开奖和购买号数范围，1-？", 
        "default_value": 30
    },
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

subscribe = Path(__file__).parent / "subscribe.json"
subscribe_list = json.loads(subscribe.read_text("utf-8")) if subscribe.is_file() else {}
def save_subscribe():
    subscribe.write_text(json.dumps(subscribe_list), encoding="utf-8")

driver = get_driver()
@driver.on_startup
async def subscribe_jobs():
    for group_id, info in subscribe_list.items():
        scheduler.add_job(
            push_calendar,
            "cron",
            args=[group_id],
            id=f"lottery_calendar_{group_id}",
            replace_existing=True,
            hour=info["hour"],
            minute=info["minute"],
        )

async def push_calendar(group_id: str):
    bot = get_bot()
    pst = await kaijiang(int(group_id))
    logger.info(f"自动开奖成功")
    await bot.send_group_msg(group_id=int(group_id), message=pst)

def calendar_subscribe(group_id: str, hour: str, minute: str) -> None:
    subscribe_list[group_id] = {"hour": hour, "minute": minute}
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
            await matcher.finish(moyu_state)
        elif "设置" in cmdarg:
            if ":" in cmdarg or "：" in cmdarg:
                matcher.set_arg("time_arg", args)
        elif "禁用" in cmdarg or "关闭" in cmdarg:
            del subscribe_list[str(event.group_id)]
            save_subscribe()
            scheduler.remove_job(f"lottery_calendar_{event.group_id}")
            await matcher.finish("每日幸运球已禁用")
        else:
            await matcher.finish("修改幸运球的参数不正确")

@kj_matcher.got("time_arg", prompt="请发送每日定时幸运球的时间，格式为：小时:分钟")
async def handle_time(
    event: GroupMessageEvent, state: T_State, time_arg: Message = Arg()
):
    state.setdefault("max_times", 0)
    time = time_arg.extract_plain_text()
    if any(cancel in time for cancel in ["取消", "放弃", "退出"]):
        await kj_matcher.finish("已退出修改幸运球时间设置")
    match = re.search(r"(\d*)[:：](\d*)", time)
    if match and match[1] and match[2]:
        calendar_subscribe(str(event.group_id), match[1], match[2])
        await kj_matcher.finish(f"每日幸运球的时间已设置为：{match[1]}:{match[2]}")
    else:
        state["max_times"] += 1
        if state["max_times"] >= 3:
            await kj_matcher.finish("你的错误次数过多，已退出定时幸运球时间设置")
        await kj_matcher.reject("设置时间失败，请输入正确的格式，格式为：小时:分钟")
#↑

#购买彩票         
@buyltnum.handle()
async def _(event: GroupMessageEvent, arg: Message = CommandArg()):
    msg = arg.extract_plain_text().strip()
    kjnum_max = Config.get_config("luckyball", "KJNUM_MAX")
    oneltcost = Config.get_config("luckyball", "ONELTCOST")
    user = await lottery.ensure(event.user_id, event.group_id)
    if user.numberlt > 0:
        await buyltnum.finish(f"你今天已经祈祷过了，数字是{user.numberlt}")
    try:
        num = int(msg)
        if num < 1 or num > kjnum_max:     
            await buyltnum.finish(f"请输入1-{kjnum_max}的数字")
    except:
        await buyltnum.finish()

    uid = event.user_id
    group = event.group_id
    gold = await BagUser.get_gold(uid, group)
    
    if gold >= oneltcost:
        await BagUser.spend_gold(uid, group, oneltcost)
        await lottery.addltnum(uid, group, num, oneltcost)              #写入玩家购买的号码，玩家加祈祷数+1,增加玩家累计消费
        await lottery_group.caipiaoleijiadd(group,oneltcost)             #增加群累计奖金池，群当日祈祷人数+1，群总祈祷次数+1
        await buyltnum.finish(f"恭喜你使用{oneltcost}金币祈祷了数字{num}")
    else:
        await buyltnum.finish("你的钱好像不够诶")


#手动开奖
@shoudong.handle()
async def _(bot: Bot, event: GroupMessageEvent):
    pst = await kaijiang(event.group_id)
    logger.info(f"手动开奖成功")
    await shoudong.finish(f"{pst}")

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