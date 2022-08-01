
from services.db_context import db

class lottery(db.Model):
    __tablename__ = "lottery"
    id = db.Column(db.Integer(), primary_key=True)
    user_qq = db.Column(db.BigInteger(), nullable=False)
    group_id = db.Column(db.BigInteger(), nullable=False)
    numberlt = db.Column(db.BigInteger(), default=0)                #玩家当日祈祷的数字
    dotimes = db.Column(db.BigInteger(), default=0)                 #玩家祈祷的次数
    userallcost = db.Column(db.BigInteger(), default=0)             #玩家累计总消费
    wintimes = db.Column(db.BigInteger(), default=0)                #玩家中奖次数
    winmoney = db.Column(db.BigInteger(), default=0)                #玩家中奖累计总额
    #historynum = db.Column(db.Array(), nullable=False, default=[])   #历史购买号码
    _idx1 = db.Index("lottery_idx1", "user_qq", "group_id", unique=True)


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
        query = cls.query.where((cls.user_qq == uid) & (cls.group_id == group_id))
        query = query.with_for_update()
        my = await query.gino.first()
        if my:
            await my.update(numberlt=num).apply()
            await my.update(dotimes=my.dotimes+1).apply()
            await my.update(userallcost=my.userallcost+costnum).apply()
        else:
            await cls.create( user_qq = uid, group_id = group_id, numberlt = num, dotimes = 1, userallcost= costnum)

    @classmethod
    async def get_all_users(cls, group_id: int):
        """
        说明：
            获取群组所有用户
        参数：
            :param group_id: 群号
        """
        if not group_id:
            query = await cls.query.gino.all()
        else:
            query = await cls.query.where((cls.group_id == group_id)).gino.all()
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
        query = cls.query.where((cls.user_qq == uid) & (cls.group_id == group_id))
        query = query.with_for_update()
        my = await query.gino.first()
        if my:
            await my.update(wintimes=my.wintimes+1).apply()
            await my.update(winmoney=my.winmoney+num).apply()
        else:
            await cls.create( user_qq = uid, group_id = group_id, wintimes = 1 ,winmoney = num)

    @classmethod
    async def ensure(cls, user_qq: int, group_id: int):
        """
        说明：
            获取用户对象
        参数：
            :param user_qq: qq号
            :param group_id: 群号
        """
        user = (
            await cls.query.where((cls.user_qq == user_qq) & (cls.group_id == group_id))
            .with_for_update()
            .gino.first()
        )
        return user or await cls.create(user_qq=user_qq, group_id=group_id) 

class lottery_group(db.Model):
    __tablename__ = "lottery_group"
    id = db.Column(db.Integer(), primary_key=True)
    group_id = db.Column(db.BigInteger(), nullable=False)
    caipiaoleiji = db.Column(db.BigInteger(), nullable=False, default=0)       #奖池
    groupdaydonum = db.Column(db.BigInteger(), default=0)                      #当日开奖前群祈祷人数
    groupalldonum = db.Column(db.BigInteger(), default=0)                      #群总祈祷次数
    groupwintime = db.Column(db.BigInteger(), default=0)                       #群总中奖人数
    _idx1 = db.Index("lottery_group_idx1", "group_id", unique=True)
    
    #@classmethod
    #async def caipiaoleijiget(cls, group_id: int) -> int:
    #    """
    #    说明：
    #        获取群累计奖金池
    #    参数：
    #        :param group_id: 群号
    #    """
    #    query = cls.query.where(cls.group_id == group_id)
    #    query = query.with_for_update()
    #    my = await query.gino.first()
    #    if my:
    #        return my.caipiaoleiji
    #    else:
    #        await cls.create( group_id=group_id, caipiaoleiji=0)
    #        return 0
    @classmethod
    async def caipiaoleijiset(cls, group_id: int, num: int):
        """
        说明：
            修改群累计奖金池
        参数：
            :param group_id: 群号
            :param num: 新累计奖金
        """
        query = cls.query.where(cls.group_id == group_id)
        query = query.with_for_update()
        my = await query.gino.first()
        if my:
            await  my.update(caipiaoleiji=num).apply()
        else:
            await cls.create( group_id=group_id, caipiaoleiji=num)
    @classmethod
    async def caipiaoleijiadd(cls, group_id: int, num: int):
        """
        说明：
            增加群累计奖金池，群当日donum+1，群总donum+1
        参数：
            :param group_id: 群号
            :param num: 待增加奖金
        """
        query = cls.query.where(cls.group_id == group_id)
        query = query.with_for_update()
        my = await query.gino.first()
        if my:
            await  my.update(caipiaoleiji=my.caipiaoleiji + num).apply()
            await  my.update(groupdaydonum=my.groupdaydonum + 1).apply()
            await  my.update(groupalldonum=my.groupalldonum + 1).apply()
        else:
            await cls.create( group_id=group_id, caipiaoleiji=num+1000,groupdaydonum=1, groupalldonum=1)
    @classmethod
    async def ensure_group(cls,group_id: int):
        """
        说明：
            获取群组对象
        参数：
            :param group_id: 群号
        """
        group = (
            await cls.query.where(cls.group_id == group_id)
            .with_for_update()
            .gino.first()
        )
        return group or await cls.create(group_id=group_id)   

    @classmethod
    async def caipiao_update(cls, group_id: int, num: int):
        """
        说明：
            更新group数据，更新群总中奖人数，清空当日开奖前群祈祷人数
        参数：
            :param group_id: 群号
            :param num: 待增加中奖人次
        """
        query = cls.query.where(cls.group_id == group_id)
        query = query.with_for_update()
        my = await query.gino.first()
        if my:
            await  my.update(groupwintime=my.groupwintime + num).apply()
            await  my.update(groupdaydonum=0).apply()
        else:
            await cls.create( group_id=group_id, groupwintime=num, groupdaydonum=0)
    
