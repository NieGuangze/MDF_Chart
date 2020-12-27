'''this file provide api to scan data in MDF File with state machine architecture'''
from asammdf import MDF
import pandas as pd
import os


def getDataFrame(mdfObj: MDF, signals: list):
    '''get can signal data frame by signal names'''
    res_df = mdfObj.to_dataframe(signals, raster=0.02)
    return res_df


class SignalProcesser(object):
    """
    class process api to calc result of signal in state
    """

    def __init__(self) -> None:
        super().__init__()

    def reset(self):
        self._res = 0

    def out(self):
        return self._res

    def calc(self):
        """
        increasing by 1
        """
        self._res += 1


class SignalStateMachine(object):
    '''
    scan signal data frame with state machine method, find in state time slot
    and execute signal processing in state
    '''

    def __init__(self, re_entry: bool = False) -> None:
        """
        set configuration
        """
        self._re_entry = re_entry
        self._sigProcs = []
        self._inState = False
        self._tStart = 0
        self._tStop = 0

    def loadProcesser(self, *sigProcs: SignalProcesser):
        """
        load signal processors to calc result in state
        """
        self._sigProcs.extend(sigProcs)

    def resetProcessor(self):
        for sigProc in self._sigProcs:
            sigProc.reset()

    def calcProcessor(self):
        for sigProc in self._sigProcs:
            sigProc.calc()

    def outProcessor(self):
        res = []
        for sigProc in self._sigProcs:
            res.append(sigProc.out())
        return res

    def run(self, entry_cond: bool, exit_cond: bool, timeStamp):
        res = []
        if self._inState:
            if exit_cond:
                self._inState = False
                self._tStop = timeStamp
                res.extend(self.outProcessor())
                return (True, self._tStart, self._tStop, res)
            elif entry_cond and self._re_entry:
                self._tStart = timeStamp
                self._tStop = timeStamp
                self.resetProcessor()
            else:
                self.calcProcessor()
        else:
            if entry_cond:
                self._inState = True
                self._tStart = timeStamp
                self._tStop = timeStamp
                self.resetProcessor()
        return (False, self._tStart, self._tStop, res)


class TurnOnDelay(object):
    """
    bool signal turn on delay
    """

    def __init__(self, delayTime=0, dT=0.02) -> None:
        super().__init__()
        self._timer = 0
        self._delayTime = delayTime
        self._dT = dT
        self._out = False

    def calc(self, inCond: bool):
        if inCond and self._timer >= self._delayTime:
            self._out = True
        elif inCond:
            self._timer += self._dT

        if not inCond:
            self._timer = 0
            self._out = False

        return self._out


class TurnOffDelay(object):
    """
    bool signal turn off delay
    """

    def __init__(self, delayTime=0, dT=0.02) -> None:
        super().__init__()
        self._timer = 0
        self._delayTime = delayTime
        self._dT = dT
        self._out = False

    def calc(self, inCond: bool):
        if not inCond and self._timer >= self._delayTime:
            self._out = False
        elif not inCond:
            self._timer += self._dT

        if inCond:
            self._timer = 0
            self._out = True
        return self._out


if __name__ == "__main__":
    dataSpace = r"E:\MDFData\TMdl_Check_TErr"

    file = r"20191127_KS20IV501_Check_TErr_37_32.dat"
    filePath = os.path.join(dataSpace, file)

    with MDF(filePath) as mdfObj:
        # mdfObj.resample(0.02)
        # ch_dict = mdfObj.channels_dbF
        smObj = SignalStateMachine()
        sigProc = SignalProcesser()
        smObj.loadProcesser(sigProc)
        entry_cond_TND = TurnOnDelay(delayTime=50)
        TOD = TurnOffDelay(delayTime=20)

        sigList = ["Epm_nEng\XCP:1", "rl_w_msg\XCP:1",
                   "ES420_TH2_CH3\ES420 / Thermo:2"]
        sig_df = getDataFrame(mdfObj, sigList)
        for i, currentTime in enumerate(sig_df.index):
            Epm_Eng = sig_df["Epm_nEng\XCP:1"].values[i]
            rl_w = sig_df["rl_w_msg\XCP:1"].values[i]

            entry_cond = \
                Epm_Eng > 3680 and \
                rl_w > 75
            entry_cond = entry_cond_TND.calc(entry_cond)
            exit_cond = Epm_Eng < 3400
            exit_cond = TOD.calc(exit_cond)

            flgGetTS, tStart, tStop, res = smObj.run(
                entry_cond, exit_cond, currentTime)
            if flgGetTS:
                print("Find Slot: [%4.2f, %4.2f], get return value: %s" % (
                    tStart, tStop, res))


# 工作量预估（15d*10h=150h)
# 内核开发（脚本实现基于信号表达式的数据窗口识别、窗口中信号计算）一周：
#   1. 信号处理状态机
#   2. 表达式支持运算符
#   3. 条件判断支持模板函数
#   4. 信号处理支持模板函数
# GUI开发（GUI封装功能）一周：
#   1. 支持选项输入
#   2. 支持配置导出、导入
#   3. 支持运算结果显示、导出
# MileStone:
#   1. 2/18春节后开发完成内核工作
#   2. 3/29完成GUI开发
