# -----------------------------------------------------------------------------
# Title       : RealAuto.py
# Author      : AugGust
# Date        : 5-Jun-2020
# Description : More Realistic Automatic Gearbox
# -----------------------------------------------------------------------------

import ac
import acsys
import math
import time
import threading
import configparser
import os
import platform
import sys
import re
import logging

if platform.architecture()[0] == "64bit":
	sysdir = os.path.dirname(__file__)+'/stdlib64'
else:
	sysdir = os.path.dirname(__file__)+'/stdlib'

sys.path.insert(0, sysdir)
os.environ['PATH'] = os.environ['PATH'] + ";."

import keyboard

#sim info stuff
from sim_info import info

maxRPM = 0
gear = 0
gas = 0
rpm = 0
speed = 0
slipping = False

initialized = False
measureIdleTime = 99999999999999


maxShiftRPM = 0
idleRPM = 0

rpmRangeSize = 0
rpmRangeTop = 0
rpmRangeBottom = 0

lastShiftTime = 0
lastShiftUpTime = 0
lastShiftDownTime = 0

#0 is eco normal driving, 4 is max
aggressiveness = 0
aggr_lbl = 0
last_inc_aggr_time = 0

#driving mode stuff
drive_mode = 0

mode_button = 0

# gear ratios
gear_ratio_list = list()
final_gear = 0
divisor = 0
gear_ratio_diff = 0
rpm_diff = 0
tire_radius = 0
maxSpeeds = list()
downShiftGear = 0
last_aggr_downshift_time = 0

# shifting when in non-manual mode
auto_shifted = False
script_gear = 0
last_gear_shift_time = 0
time_in_neutral = 0
is_temp_manual = False
last_drive_mode = 0
tempManualTrue = 0
tempManualFalse = 0
tempManualCalled = 0
shifted_from_neutral = 0
last_gears = []

debug_flag = 0
last_get_info_time = 0

# for keyboard switching between modes
pressed = False

def getPaths(carName):
    driveTrainPath = os.getcwd() + "\\content\\cars\\" + carName + "\\data\\drivetrain.ini"
    enginePath = os.getcwd() + "\\content\\cars\\" + carName + "\\data\\engine.ini"
    tyresPath = os.getcwd() + "\\content\\cars\\" + carName + "\\data\\tyres.ini"
    return driveTrainPath, enginePath, tyresPath

def getGearRatios(driveTrainPath):
    config = configparser.RawConfigParser(strict = False)
    config.read(driveTrainPath, encoding="utf8")
    gearCount = config.get("GEARS", "count")
    gearCount = int(re.search(r'[\d\.]+', gearCount).group())
    gear_list = []
    for i in range(gearCount):
        gearName = "GEAR_" + str(i + 1)
        gear_list.append(config.getfloat("GEARS", gearName))
    
    return gear_list

def getFinalGearRatio(driveTrainPath):
    config = configparser.RawConfigParser(strict = False)
    config.read(driveTrainPath, encoding="utf8")
    finalGearRatio = config.get("GEARS", "final")
    finalGearRatio = float(re.search(r'[\d\.]+', finalGearRatio).group())
    return finalGearRatio

def getRedline(enginePath):
    config = configparser.RawConfigParser(strict = False)
    config.read(enginePath, encoding="utf8")
    redline = config.get("ENGINE_DATA", "LIMITER")
    redline = float(re.search(r'[\d\.]+', redline).group())
    return redline

def getTireDiameter(tyresPath):
    config = configparser.RawConfigParser(strict = False)
    config.read(tyresPath, encoding="utf8")
    tireDiameter = config.get("FRONT", "RADIUS")
    tireDiameter = float(re.search(r'[\d\.]+', tireDiameter).group()) * 2 * 39.3701
    return tireDiameter

def getMaxSpeeds(carName, scaling_factor = 3):
    driveTrainPath, enginePath, tyresPath = getPaths(carName)
    gearRatios = getGearRatios(driveTrainPath)
    finalGearRatio = getFinalGearRatio(driveTrainPath)
    redline = getRedline(enginePath)
    tireDiameter = getTireDiameter(tyresPath)
    return [(redline * tireDiameter * 60 * scaling_factor) / (ratio * finalGearRatio * 63360) for ratio in gearRatios]

def acMain(ac_version):
    global aggr_lbl, mode_button
    app_window = ac.newApp("Realistic Auto")
    ac.setSize(app_window, 180, 240)

    mode_label = ac.addLabel(app_window, "Drive Mode")
    ac.setFontAlignment(mode_label, "center")
    ac.setPosition(mode_label, 90, 40)

    mode_button = ac.addButton(app_window, "Manual")
    ac.setPosition(mode_button, 30, 65)
    ac.setSize(mode_button, 120, 25)
    ac.addOnClickedListener(mode_button, toggleDriveMode)

    debug_lbl = ac.addLabel(app_window, "Debug Info")
    ac.setPosition(debug_lbl, 20, 110)
    aggr_lbl = ac.addLabel(app_window, "")
    ac.setPosition(aggr_lbl, 20, 135)
    initializeInfo()
    return


def acUpdate(deltaT):
    keyboardUpdateDriveMode()
    getInfo()
    if drive_mode > 0:
        setRPMRangeSize()
        analyzeInput(deltaT)
        makeDecision()


modes = ["Manual", "Auto: Normal", "Auto: Sport", "Auto: Eco"]


def toggleDriveMode(*args):
    global mode_button, drive_mode
    drive_mode += 1
    drive_mode = drive_mode%4
    ac.setText(mode_button, modes[drive_mode])


def keyboardUpdateDriveMode():
    global pressed
    try: 
        if keyboard.is_pressed(' '):
            if not pressed: 
                toggleDriveMode()
            pressed = True
        else:
            pressed = False
    except:
        return


def setToTempManual(set):
    global mode_button, drive_mode, script_gear, last_gear_shift_time, is_temp_manual, tempManualTrue, tempManualFalse, tempManualCalled, last_drive_mode
    tempManualCalled += 1
    if (set):
        script_gear = ac.getCarState(0,acsys.CS.Gear) - 1
        last_drive_mode = drive_mode
        last_gear_shift_time = time.time()
        is_temp_manual = True
        drive_mode = 0
        tempManualTrue += 1
        ac.setText(mode_button, modes[drive_mode])
    else:
        is_temp_manual = False
        drive_mode = last_drive_mode
        drive_mode = drive_mode%4
        tempManualFalse += 1
        ac.setText(mode_button, modes[drive_mode])


gas_thresholds =    [[0, 0, 0, 0],
                    [0.95, 0.4, 12, 0],
                    [0.8, 0.4, 24, 0.5],
                    [1, 0.5, 4, 0]]


def analyzeInput(deltaT):
    global aggressiveness, aggr_lbl, rpmRangeTop, rpmRangeBottom, last_inc_aggr_time, tempManualTrue, tempManualFalse, tempManualCalled
    new_aggr = min(1, (gas - gas_thresholds[drive_mode][1]) / (gas_thresholds[drive_mode][0] - gas_thresholds[drive_mode][1]))

    if new_aggr > aggressiveness and gear > 0:
        aggressiveness = new_aggr
        last_inc_aggr_time = time.time()

    if time.time() > last_inc_aggr_time + 2:
        aggressiveness -= (deltaT / gas_thresholds[drive_mode][2])

    aggressiveness = max(aggressiveness, gas_thresholds[drive_mode][3])

    rpmRangeTop = idleRPM + 1000 + ((maxShiftRPM - idleRPM - 700)*aggressiveness)
    if rpmRangeTop > maxShiftRPM:
        rpmRangeTop=maxShiftRPM
    # else: 
    #     rpmRangeTop = idleRPM + 1000 + ((maxShiftRPM - idleRPM - 700)*aggressiveness)
    # if time.time() < last_aggr_downshift_time + 1:
    #     rpmRangeBottom = 0
    # else:
    #     rpmRangeBottom = max(idleRPM + (min(gear, 6) * 80), rpmRangeTop - rpmRangeSize)
    if aggressiveness == 1:
        rpmRangeBottom = 0
    else:
        rpmRangeBottom = max(idleRPM + (min(gear, 6) * 80), rpmRangeTop - rpmRangeSize)

    

    debugText = "Aggressiveness: " + str(round(aggressiveness, 2)) + "\nRpm Top: " + str(round(rpmRangeTop)) + "\nRpm Bottom: " + str(round(rpmRangeBottom))
    def formatDebugText(text, value):
        return ("\n" + text + " " + str(value))
    # debugText += formatDebugText("gear", gear)
    # debugText += formatDebugText("script gear", script_gear)
    # debugText += formatDebugText("auto shifted", auto_shifted)
    # debugText += formatDebugText("maxShiftRPM", maxShiftRPM)
    debugText += formatDebugText("temp manual", is_temp_manual)
    debugText += formatDebugText("current rpm", str(round(rpm)))
    # debugText += formatDebugText("temp manual true count", tempManualTrue)
    # debugText += formatDebugText("temp manual false count", tempManualFalse)
    # debugText += formatDebugText("temp manual called count", tempManualCalled)
    debugText += formatDebugText("drive mode", drive_mode)
    # debugText += formatDebugText("shifted from neutral", shifted_from_neutral)
    # debugText += formatDebugText("time in neutral", time_in_neutral)
    debugText += formatDebugText("gear", gear)
    debugText += formatDebugText("last gear shift time", last_gear_shift_time)
    ac.setText(aggr_lbl, debugText)

def setRPMRangeSize():
    global divisor, rpmRangeSize, gear_ratio_diff, rpm_diff
    divisor = 2
    rpmRangeSize = (maxRPM - idleRPM)/divisor

def makeDecision():
    global last_aggr_downshift_time, downShiftGear
    if time.time() < lastShiftTime + 0.1 or gear < 1 or time.time() < lastShiftUpTime + 1:
        return
        
    if aggressiveness == 1:
        last_aggr_downshift_time = time.time()
        # figure out which gear to downshift to
        downshiftGearPossible = 0
        while downshiftGearPossible < len(maxSpeeds) and maxSpeeds[downshiftGearPossible] < speed * 0.621:
            downshiftGearPossible += 1
        downShiftGear = max(1, downshiftGearPossible + 1) # add one because maxSpeeds array was 0-indexd
        if speed * 0.621 < 35:
            downShiftGear = max(downShiftGear, 2)
        if downShiftGear < gear:
            for _ in range(gear - downShiftGear):
                shiftDown()
            return
    if rpm > rpmRangeTop and not slipping and time.time() > lastShiftDownTime + 1:
        shiftUp()
    elif rpm < rpmRangeBottom and not slipping and gear > 1:
        shiftDown()


def getInfo():
    global gear, gas, rpm, speed, slipping, maxSpeeds, is_temp_manual, tempManualCalled, auto_shifted, shifted_from_neutral, last_gears, tempManualTrue, tempManualFalse, last_gear_shift_time, time_in_neutral, last_get_info_time
    last_get_info_time = time.time()
    if not initialized:
        initializeInfo()
    gas = ac.getCarState(0,acsys.CS.Gas)
    rpm = ac.getCarState(0,acsys.CS.RPM)
    speed = ac.getCarState(0,acsys.CS.SpeedKMH)

    # set to temporary manual if we detect that the driver shifted while in non-manual mode
    if gear == 0:
        time_in_neutral += time.time() - last_get_info_time
    else:
        time_in_neutral = 0
    if gear != ac.getCarState(0,acsys.CS.Gear) - 1:
        shifted_from_neutral = time_in_neutral > 0.45
        last_gears = [gear]
        gear = ac.getCarState(0,acsys.CS.Gear) - 1
        if auto_shifted == True:
            script_gear = gear
            auto_shifted = False
        elif time.time() - last_gear_shift_time > 0.45 and drive_mode != 0 and not shifted_from_neutral:
            tempManualTrue += 1
            #setToTempManual(True)
        last_gear_shift_time = time.time()
    elif is_temp_manual:
        if time.time() - last_gear_shift_time > 7:
            tempManualFalse += 1
            last_gear_shift_time = time.time()
            setToTempManual(False)

    maxSlip = ac.getCarState(0,acsys.CS.NdSlip)[0]
    if ac.getCarState(0,acsys.CS.NdSlip)[1] > maxSlip:
        maxSlip = ac.getCarState(0,acsys.CS.NdSlip)[1]
    if ac.getCarState(0,acsys.CS.NdSlip)[2] > maxSlip:
        maxSlip = ac.getCarState(0,acsys.CS.NdSlip)[2]
    if ac.getCarState(0,acsys.CS.NdSlip)[3] > maxSlip:
        maxSlip = ac.getCarState(0,acsys.CS.NdSlip)[3]
    if maxSlip > 1:
        slipping = True
    else:
        slipping = False

    maxSpeeds = getMaxSpeeds(ac.getCarName(0))
    # add offsets
    maxSpeeds[0] -= 15
    for i in range(1, len(maxSpeeds)):
        maxSpeeds[i] -=7

            

def initializeInfo():
    global maxRPM, maxShiftRPM, measureIdleTime, idleRPM, initialized, gear_ratio_list, final_gear, tire_radius
    if not (info.static.maxRpm == 0):
        maxRPM = info.static.maxRpm
        maxShiftRPM = maxRPM * 0.95
        if measureIdleTime == 99999999999999:
            measureIdleTime = time.time() + 3
    
    if not initialized:
        if time.time() > measureIdleTime:
            idleRPM = ac.getCarState(0,acsys.CS.RPM)
            initialized = True

        carName = ac.getCarName(0)
        driveTrainPath = os.getcwd() + "\\content\\cars\\" + carName + "\\data\\drivetrain.ini"
        config = configparser.RawConfigParser(strict = False)
        config.read(driveTrainPath, encoding="utf8")
        gearCount = config.get("GEARS", "count")
        gearCount = int(re.search(r'[\d\.]+', gearCount).group())
        final_gear = config.get("GEARS", "final")
        final_gear = float(re.search(r'[\d\.]+', final_gear).group())
        gear_ratio_list = [config.getfloat("GEARS", "GEAR_" + str(i + 1)) for i in range(gearCount)]

        tiresPath = os.getcwd() + "\\content\\cars\\" + carName + "\\data\\tyres.ini"
        tiresConfig = configparser.RawConfigParser(strict = False)
        tiresConfig.read(tiresPath, encoding="utf8")
        tire_radius = tiresConfig.get("FRONT", "RADIUS")
        tire_radius = float(re.search(r'[\d\.]+', tire_radius).group())


# fake pressing the P key, 
# trigerring an upshifting if the key is properly mapped in AC
def shiftUp():
    global lastShiftTime, lastShiftUpTime, auto_shifted
    # actually press the key
    keyboard.press_and_release('p')
    ac.setGear(ac.getCarState(0, acsys.CS.Gear) + 1)
    # update the last shifting times
    lastShiftTime       = time.time()
    lastShiftUpTime     = time.time()
    auto_shifted = True


# fake pressing the O key, 
# trigerring a downshift if the key is properly mapped in AC
def shiftDown():
    global lastShiftTime, lastShiftDownTime, auto_shifted
    # actually press the key
    keyboard.press_and_release('o')
    ac.setGear(ac.getCarState(0, acsys.CS.Gear) - 1)
    # update the last shifting times
    lastShiftTime       = time.time()
    lastShiftDownTime   = time.time()
    auto_shifted = True