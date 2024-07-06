import os
import configparser
import re
import sys

# example carName -> sghh_camry2009

def getPaths(carName):
    driveTrainPath = os.getcwd() + "\\content\\cars\\" + carName + "\\data\\drivetrain.ini"
    enginePath = os.getcwd() + "\\content\\cars\\" + carName + "\\data\\engine.ini"
    tyresPath = os.getcwd() + "\\content\\cars\\" + carName + "\\data\\tyres.ini"
    return driveTrainPath, enginePath, tyresPath

def getGearRatios(driveTrainPath):
    config = configparser.ConfigParser()
    config.read(driveTrainPath)
    gearCount = config.get("GEARS", "count")
    gearCount = int(re.search(r'[\d\.]+', gearCount).group())
    gear_list = []
    for i in range(gearCount):
        gearName = "GEAR_" + str(i + 1)
        gear_list.append(config.getfloat("GEARS", gearName))
    
    return gear_list

def getFinalGearRatio(driveTrainPath):
    config = configparser.ConfigParser()
    config.read(driveTrainPath)
    finalGearRatio = config.get("GEARS", "final")
    finalGearRatio = float(re.search(r'[\d\.]+', finalGearRatio).group())
    return finalGearRatio

def getRedline(enginePath):
    config = configparser.ConfigParser()
    config.read(enginePath)
    redline = config.get("ENGINE_DATA", "LIMITER")
    redline = float(re.search(r'[\d\.]+', redline).group())
    return redline

def getTireDiameter(tyresPath):
    config = configparser.ConfigParser()
    config.read(tyresPath)
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

if __name__ == "__main__":
    assert len(sys.argv) <= 3, "Need to pass in exactly one car name, and optionally a scaling factor"
    carName = sys.argv[1]
    scaling_factor = 3 if len(sys.argv) < 3 else float(sys.argv[2])
    maxSpeeds = getMaxSpeeds(carName, scaling_factor)

    print(f"Max gear speeds for {carName} (in mph):")
    for i in range(len(maxSpeeds)):
        print(f"Gear {i + 1}: ", maxSpeeds[i])


