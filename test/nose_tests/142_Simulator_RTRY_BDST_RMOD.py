#!/usr/bin/env python
#
import epics
import unittest
import os
import sys
import time
from motor_lib import motor_lib
lib = motor_lib()
###



# Values to be used for backlash test
# Note: Make sure to use different values to hae a good
# test coverage
myVELO = 10.0   # positioning velocity
myACCL =  1.0   # Time to VELO, seconds
myAR   = myVELO / myACCL # acceleration, mm/sec^2

myJVEL = 5.0    # Jogging velocity
myJAR  = 6.0    # Jogging acceleration, mm/sec^2

myBVEL = 2.0    # backlash velocity
myBACC = 1.5    # backlash acceleration, seconds
myBAR  = myBVEL / myBACC  # backlash acceleration, mm/sec^2
myRTRY   = 3
myDLY    =  0.0
myBDST   = 24.0 # backlash destination, mm
myFRAC   = 1.0  #
myPOSlow = 48   #
myPOSmid = 72   # low + BDST
myPOShig = 96   # low + 2*BDST



motorRMOD_D = 0 # "Default"
motorRMOD_A = 1 # "Arithmetic"
motorRMOD_G = 2 # "Geometric"
motorRMOD_I = 3 # "In-Position"

#How we move: Absolute (without encoder) or relative (with encode via UEIP)
use_abs = 0
use_rel = 1
# Note: motorRMOD_I is always absolute !



def motorInitAll(tself, motor, tc_no):
    lib.setValueOnSimulator(motor, tc_no, "nAmplifierPercent", 100)
    lib.setValueOnSimulator(motor, tc_no, "bAxisHomed",          1)
    lib.setValueOnSimulator(motor, tc_no, "fLowHardLimitPos",   15)
    lib.setValueOnSimulator(motor, tc_no, "fHighHardLimitPos", 165)
    lib.setValueOnSimulator(motor, tc_no, "setMRES_23", 0)
    lib.setValueOnSimulator(motor, tc_no, "setMRES_24", 0)

    # Prepare parameters for jogging and backlash
    epics.caput(motor + '.VELO', myVELO)
    epics.caput(motor + '.ACCL', myACCL)

    epics.caput(motor + '.JVEL', myJVEL)
    epics.caput(motor + '.JAR',  myJAR)

    epics.caput(motor + '.BVEL', myBVEL)
    epics.caput(motor + '.BACC', myBACC)
    epics.caput(motor + '.BDST', myBDST)
    epics.caput(motor + '.FRAC', myFRAC)
    epics.caput(motor + '.RTRY', myRTRY)
    epics.caput(motor + '.DLY',  myDLY)


def motorInitTC(tself, motor, tc_no, rmod, encRel):
    epics.caput(motor + '.RMOD', rmod)
    epics.caput(motor + '.UEIP', encRel)


def setMotorStartPos(tself, motor, tc_no, startpos):
    lib.setValueOnSimulator(motor, tc_no, "fActPosition", startpos)
    # Run a status update and a sync
    epics.caput(motor + '.STUP', 1)
    epics.caput(motor + '.SYNC', 1)




def positionAndBacklash(tself, motor, tc_no, rmod, encRel, motorStartPos, motorEndPos):
    ###########
    # expected and actual
    fileName = "/tmp/" + motor.replace(':', '-') + "-" + str(tc_no)
    expFileName = fileName + ".exp"
    actFileName = fileName + ".act"
    dbgFileName = fileName + ".dbg"

    motorInitTC(tself, motor, tc_no, rmod, encRel)
    setMotorStartPos(tself, motor, tc_no, motorStartPos)
    lib.setValueOnSimulator(motor, tc_no, "bManualSimulatorMode", 1)
    time.sleep(2)
    lib.setValueOnSimulator(motor, tc_no, "log", actFileName)
    time.sleep(2)
    #
    epics.caput(motor + '.VAL', motorEndPos, wait=True)
    lib.setValueOnSimulator(motor, tc_no, "dbgCloseLogFile", "1")
    time.sleep(2)
    lib.setValueOnSimulator(motor, tc_no, "bManualSimulatorMode", 0)

    # Create a "expected" file
    expFile=open(expFileName, 'w')
    if dbgFileName != None:
        dbgFile=open(dbgFileName, 'w')
    else:
        dbgFile = None
    # Positioning
    # 2 different ways to move:
    # - Within the backlash distance and into the backlash direction:
    #   single move with back lash parameters
    # - against the backlash direction -or- bigger than the backlash distance:
    #   two moves, first with moving, second with backlash parameters

    cnt = 1 + int(epics.caget(motor + '.RTRY'))
    lib.writeExpFileRMOD_X(motor, tc_no, rmod, dbgFile, expFile, cnt, encRel, motorStartPos, motorEndPos)

    expFile.close()
    if dbgFileName != None:
        dbgFile.close()
    lib.setValueOnSimulator(motor, tc_no, "dbgCloseLogFile", "1")

    lib.cmpUnlinkExpectedActualFile(dbgFileName, expFileName, actFileName)



class Test(unittest.TestCase):
    motor = os.getenv("TESTEDMOTORAXIS")

    def test_TC_14200(self):
        motorInitAll(self, self.motor, 14200)

    # motorRMOD_D = 0 # "Default"
    # position forward & backlash compensation, absolute
    def test_TC_14201(self):
        positionAndBacklash(self, self.motor, 14201, motorRMOD_D, use_abs, myPOSlow, myPOShig)

    # position forward & backlash compensation, relative
    def test_TC_14202(self):
        positionAndBacklash(self, self.motor, 14202, motorRMOD_D, use_rel, myPOSlow, myPOShig)

    # position backward & backlash compensation, absolute
    def test_TC_14203(self):
        positionAndBacklash(self, self.motor, 14203, motorRMOD_D, use_abs, myPOShig, myPOSlow)

    # position backward & backlash compensation, relative
    def test_TC_14204(self):
        positionAndBacklash(self, self.motor, 14204, motorRMOD_D, use_rel, myPOShig, myPOSlow)

    # position forward inside backlash range, absolute
    def test_TC_14205(self):
        positionAndBacklash(self, self.motor, 14205, motorRMOD_D, use_abs, myPOSmid, myPOSlow)

    # position forward inside backlash range, relative
    def test_TC_14206(self):
        positionAndBacklash(self, self.motor, 14206, motorRMOD_D, use_rel, myPOSmid, myPOSlow)

    # position forward inside backlash range, absolute
    def test_TC_14207(self):
        positionAndBacklash(self, self.motor, 14207, motorRMOD_D, use_abs, myPOSlow, myPOSmid)

    # position forward inside backlash range, relative
    def test_TC_14208(self):
        positionAndBacklash(self, self.motor, 14208, motorRMOD_D, use_rel, myPOSlow, myPOSmid)

    ###############################################################################
    # motorRMOD_A
    # position forward & backlash compensation, absolute
    def test_TC_14211(self):
        positionAndBacklash(self, self.motor, 14211, motorRMOD_A, use_abs, myPOSlow, myPOShig)

    # position forward & backlash compensation, relative
    def test_TC_14212(self):
        positionAndBacklash(self, self.motor, 14212, motorRMOD_A, use_rel, myPOSlow, myPOShig)

    # position backward & backlash compensation, absolute
    def test_TC_14213(self):
        positionAndBacklash(self, self.motor, 14213, motorRMOD_A, use_abs, myPOShig, myPOSlow)

    # position backward & backlash compensation, relative
    def test_TC_14214(self):
        positionAndBacklash(self, self.motor, 14214, motorRMOD_A, use_rel, myPOShig, myPOSlow)

    # position forward inside backlash range, absolute
    def test_TC_14215(self):
        positionAndBacklash(self, self.motor, 14215, motorRMOD_A, use_abs, myPOSmid, myPOSlow)

    # position forward inside backlash range, relative
    def test_TC_14216(self):
        positionAndBacklash(self, self.motor, 14216, motorRMOD_A, use_rel, myPOSmid, myPOSlow)

    # position forward inside backlash range, absolute
    def test_TC_14217(self):
        positionAndBacklash(self, self.motor, 14217, motorRMOD_A, use_abs, myPOSlow, myPOSmid)

    # position forward inside backlash range, relative
    def test_TC_14218(self):
        positionAndBacklash(self, self.motor, 14218, motorRMOD_A, use_rel, myPOSlow, myPOSmid)

    ###############################################################################
    # motorRMOD_G
    # position forward & backlash compensation, absolute
    def test_TC_14221(self):
        positionAndBacklash(self, self.motor, 14221, motorRMOD_G, use_abs, myPOSlow, myPOShig)

    # position forward & backlash compensation, relative
    def test_TC_14222(self):
        positionAndBacklash(self, self.motor, 14222, motorRMOD_G, use_rel, myPOSlow, myPOShig)

    # position backward & backlash compensation, absolute
    def test_TC_14223(self):
        positionAndBacklash(self, self.motor, 14223, motorRMOD_G, use_abs, myPOShig, myPOSlow)

    # position backward & backlash compensation, relative
    def test_TC_14224(self):
        positionAndBacklash(self, self.motor, 14224, motorRMOD_G, use_rel, myPOShig, myPOSlow)

    # position forward inside backlash range, absolute
    def test_TC_14225(self):
        positionAndBacklash(self, self.motor, 14225, motorRMOD_G, use_abs, myPOSmid, myPOSlow)

    # position forward inside backlash range, relative
    def test_TC_14226(self):
        positionAndBacklash(self, self.motor, 14226, motorRMOD_G, use_rel, myPOSmid, myPOSlow)

    # position forward inside backlash range, absolute
    def test_TC_14227(self):
        positionAndBacklash(self, self.motor, 14227, motorRMOD_G, use_abs, myPOSlow, myPOSmid)

    # position forward inside backlash range, relative
    def test_TC_14228(self):
        positionAndBacklash(self, self.motor, 14228, motorRMOD_G, use_rel, myPOSlow, myPOSmid)


    ###############################################################################
    # motorRMOD_I
    # position forward & backlash compensation, absolute
    def test_TC_14231(self):
        positionAndBacklash(self, self.motor, 14231, motorRMOD_I, use_abs, myPOSlow, myPOShig)

    # position forward & backlash compensation, relative
    def test_TC_14232(self):
        positionAndBacklash(self, self.motor, 14232, motorRMOD_I, use_rel, myPOSlow, myPOShig)

    # position backward & backlash compensation, absolute
    def test_TC_14233(self):
        positionAndBacklash(self, self.motor, 14233, motorRMOD_I, use_abs, myPOShig, myPOSlow)

    # position backward & backlash compensation, relative
    def test_TC_14234(self):
        positionAndBacklash(self, self.motor, 14234, motorRMOD_I, use_rel, myPOShig, myPOSlow)

    # position forward inside backlash range, absolute
    def test_TC_14235(self):
        positionAndBacklash(self, self.motor, 14235, motorRMOD_I, use_abs, myPOSmid, myPOSlow)

    # position forward inside backlash range, relative
    def test_TC_14236(self):
        positionAndBacklash(self, self.motor, 14236, motorRMOD_I, use_rel, myPOSmid, myPOSlow)

    # position forward inside backlash range, absolute
    def test_TC_14237(self):
        positionAndBacklash(self, self.motor, 14237, motorRMOD_I, use_abs, myPOSlow, myPOSmid)

    # position forward inside backlash range, relative
    def test_TC_14238(self):
        positionAndBacklash(self, self.motor, 14238, motorRMOD_I, use_rel, myPOSlow, myPOSmid)
