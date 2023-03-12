from tortoise import fields
from services.db_context import Model

class lottery(Model):

    class Meta:
        table = "lottery"
        unique_together = ("user_qq", "group_id")

    id = fields.IntField(pk=True, generated=True, auto_increment=True) # 自增id
    user_qq = fields.BigIntField() # 用户id
    group_id = fields.BigIntField() # 群聊id
    numberlt = fields.BigIntField(default=0, null=True)                #玩家当日祈祷的数字
    dotimes = fields.BigIntField(default=0, null=True)                 #玩家祈祷的次数
    userallcost = fields.BigIntField(default=0, null=True)             #玩家累计总消费
    wintimes = fields.BigIntField(default=0, null=True)                #玩家中奖次数
    winmoney = fields.BigIntField(default=0, null=True)                #玩家中奖累计总额

    @classmethod
    async def addltnum(cls, uid: int,  group_id: int, num: int, costnum:int):
        """
        说明：
            写入玩家购买的号码，numberlt=数字，dotimes+1,增加玩家累计消费
        参数：
            :param user_qq: qq号
            :param group_id: 群号
            :param num: 玩家购买的号码
            :param costnum:玩家花费金币
        """
        my, _ = await cls.get_or_create(user_qq=uid, group_id=group_id)
        my.numberlt = num
        my.dotimes = my.dotimes + 1
        my.userallcost = my.userallcost + costnum
        await my.save()

    @classmethod
    async def get_all_users(cls, group_id: int):
        """
        说明：
            获取群组所有用户
        参数：
            :param group_id: 群号
        """
        if not group_id:
            query = await cls.all()
        else:
            query = await cls.filter(group_id = group_id).all()
        return query

    @classmethod
    async def windataup(cls, uid: int, group_id: int ,  num: int):
        """
        说明：
            中奖玩家更新数据
        参数：
            :param user_qq: qq号
            :param group_id: 群号
            :param num: 奖金
        """
        my, _ = await cls.get_or_create(user_qq=uid, group_id=group_id)
        my.wintimes = my.wintimes + 1
        my.winmoney = my.winmoney + num
        await my.save()

    @classmethod
    async def ensure(cls, user_qq: int, group_id: int):
        """
        说明：
            获取用户对象
        参数：
            :param user_qq: qq号
            :param group_id: 群号
        """
        user, _ = await cls.get_or_create(user_qq=user_qq, group_id=group_id)
        return user

class lottery_group(Model):

    class Meta:
        table = "lottery_group"

    id = fields.IntField(pk=True, generated=True, auto_increment=True) # 自增id
    group_id = fields.BigIntField(unique=True) # 群聊id
    caipiaoleiji = fields.BigIntField(default=0)                               #奖池
    groupdaydonum = fields.BigIntField(default=0, null=True)                   #当日开奖前群祈祷人数
    groupalldonum = fields.BigIntField(default=0, null=True)                   #群总祈祷次数
    groupwintime = fields.BigIntField(default=0, null=True)                    #群总中奖人数

    @classmethod
    async def caipiaoleijiset(cls, group_id: int, num: int):
        """
        说明：
            修改群累计奖金池
        参数：
            :param group_id: 群号
            :param num: 新累计奖金
        """
        my, _ = await cls.get_or_create(group_id=group_id)
        my.caipiaoleiji = num
        await my.save()

    @classmethod
    async def caipiaoleijiadd(cls, group_id: int, num: int):
        """
        说明：
            增加群累计奖金池，群当日donum+1，群总donum+1
        参数：
            :param group_id: 群号
            :param num: 待增加奖金
        """
        my, _ = await cls.get_or_create(group_id=group_id)
        my.caipiaoleiji = my.caipiaoleiji + num
        my.groupdaydonum = my.groupdaydonum + 1
        my.groupalldonum = my.groupalldonum + 1
        await my.save()

    @classmethod
    async def ensure_group(cls,group_id: int):
        """
        说明：
            获取群组对象
        参数：
            :param group_id: 群号
        """
        group, _ = await cls.get_or_create(group_id=group_id)
        return group  

    @classmethod
    async def caipiao_update(cls, group_id: int, num: int):
        """
        说明：
            更新group数据，更新群总中奖人数，清空当日开奖前群祈祷人数
        参数：
            :param group_id: 群号
            :param num: 待增加中奖人次
        """
        my, _ = await cls.get_or_create(group_id=group_id)
        my.groupwintime = my.groupwintime + num
        my.groupdaydonum = 0
        await my.save()

