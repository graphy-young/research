''' Module import '''
import honeywell_hpma115s0 as hw # for connecting pm sensor
import pymysql # to CRUD data with database
import keys # including database connection info
import pandas as pd # to read local-stored data
from os import system, getresuid, getlogin # to execute linux command
from os.path import isfile, abspath # check whether local file exists
from datetime import datetime # to load measured & executed time
from modules.ds3231 import SDL_DS3231


''' function definition  '''
def logger(*args):
    """
        Print log message with excecuting file name, timestamp.
        *** All parameters should be on string-type!
    """
    message = f"[{__file__} {str(datetime.now())}] {str(' '.join(args))}"
    print(message)

def dbLogger(fileDescriptor, *args):
    """
        Insert log message into remote DB server
    """

    if str(type(fileDescriptor))[8:-2] == 'int' and (0 <= int(fileDescriptor) <= 2):
        pass
    else:
        raise WrongInputException

    connection, cursor = connectDB()
    message = str(' '.join(args))

    lTableName = 'command_log'
    lColumnList = ['station_code', 'execution_time', 'user_account', 'uid', 'executed_file', 'file_descriptor', 'command']
    
    station_code = getStationCode()
    execution_time = str(datetime.now())
    user_account = getlogin()
    uid = str(getresuid()[0])
    executed_file = abspath(__file__)
    file_descriptor = fileDescriptor

    query = f"INSERT INTO {lTableName} ({', '.join(lColumnList)}) VALUES ('{station_code}', '{execution_time}', '{user_account}', {uid}, '{executed_file}', {file_descriptor}, '{message}');"
    
    cursor.execute(query)
    connection.commit()
    logger('DB log insertion completed.')

def syncTime():
    """ 
        Sync device's time via remote time server then write in DS3231 RTC module.
        If failed, read datetime from RTC.
    """
    try:
        # Load real time from external server. if there's no network connection, it occurs errors
        system('sudo rdate -s time.bora.net')
        logger('System time sync got successful')
        SDL_DS3231().write_now()
        logger('Datetime in RTC module has been overwritten with server time')

    except Exception as e:
        msg = (f'time sync got failed! ERROR: {str(e)}')
        rtc_datetime = SDL_DS3231().read_datetime() # returns datetime object
        system(f'date {rtc_datetime.strftime("%m%d%H%M%y.%S")}')
        logger(f'Reading datetime from RTC module complete now: {str(rtc_datetime)}')
        logError(e, msg)

def connectDB():
    """
       Connect to MySQL database server, returning connection & cursor objects. 
    """
    try:
        connection = pymysql.connect(host=keys.host, port=keys.port, 
                                    user=keys.userName, password=keys.password, 
                                    database=keys.dbName)
        cursor = connection.cursor()
        logger('DB connection Established.')
        return connection, cursor
    except Exception as e:
        msg = (f'DB connection failed! ERROR: {str(e)}')
        logError(e, msg)

def getSerial():
  """ 
    Extract serial from /proc/cpuinfo file what RPi OS having in itself
    This works only Rasberry Pi OS(former named Raspbian)
  """
  cpuSerial = "0000000000000000" # 16 bytes

  try:
    with open('/proc/cpuinfo', 'r') as f: # Read Raspberry Pi's hardware info file
        for line in f:
            if line[0:6]=='Serial': # Find the line starting with "Serial" to search RPi's serial number
                cpuSerial = line[10:26]

  except Exception as e:
    msg = f"Getting Serial code from RPi failed! ERROR: : {[str(e)]}"
    logError(e, msg)
    #cpuSerial = "UNKNOWN_SERIAL0"
  return cpuSerial

def getStationCode():
    """
        Get station code using RPi's CPU seiral code
    """
    try:
        connection, cursor = connectDB()

        rpiSerial = getSerial()

        query = f"SELECT station_code FROM station_info WHERE serial_code = '{rpiSerial}';"
        cursor.execute(query)
        stationCode = cursor.fetchone()[0]
        logger(f"Station code '{stationCode}' Fetched from DB successfully")

    except Exception as e:
        msg = f'Searching station code from DB failed! ERROR: {[str(e)]}'
        logError(e, msg)

    finally:
        connection.close()

    return stationCode

def logError(er, *args):
    """
        Log error data to database server
    """
    logger('ERROR OCCURED! EXECUTE LOG ERROR PROCESS.')

    station_code = getStationCode()
    execution_time = str(datetime.now())
    user_account = getlogin()
    uid = str(getresuid()[0]) # originally returns tuple (ruid, euid, suid)
    executed_file = abspath(__file__)
    errors = str(er)
    escapeMessage = str(' '.join(args))

    try:
        connection, cursor = connectDB()
        eFileName = '/home/pi/raspmeasure/error.tsv'
        eTableName = 'command_log'
        eColumnList = ['station_code', 'execution_time', 'user_account', 'uid', 'executed_file', 'file_descriptor', 'command']

        if isfile(eFileName):
            logger('Found previous log that could not be saved properly to DB server. Try again to save those...')
            errorFile = pd.read_csv(eFileName, encoding='utf-8', names=eColumnList, delimiter="\t")
            errorFile = errorFile.astype({'station_code': 'str'})
            # When pandas reads csv without any dtype parameter, it reads station code under 10 as integer 0, not '00'.
            errorFile['station_code'] = errorFile['station_code'].apply(lambda x: '0'+str(x) if int(x) < 10 else x)
            errorFile = list(errorFile.values.tolist())
            for row in errorFile:
                row[3] = connection.escape_string(row[3])
            query = f"INSERT INTO {eTableName} ({', '.join(eColumnList)}) VALUES (%s, %s, %s, %s, %s, %s, %s);"
            cursor.executemany(query, errorFile)
            connection.commit()
            if int(cursor.rowcount) > 1:
                messageVerb = 'were'
            else:
                messageVerb = 'was'
            logger('Previous', str(cursor.rowcount), 'log', messageVerb, 'inserted.')
            system(f'rm -rf {eFileName}')
            logger(f'{eFileName} deleted.')
        query = f"INSERT INTO {eTableName} ({', '.join(eColumnList)}) VALUES ('{station_code}', '{execution_time}', '{user_account}', {uid}, '{executed_file}', 2, '{connection.escape_string(errors)}');"
        cursor.execute(query)
        connection.commit()
        logger(f"Error data '{station_code}', {execution_time}, '{user_account}', {uid}, {executed_file}, 2, {errors} insertion success.")

    except Exception as e:
        logger(f'Error logging process failed due to ERROR: {str(e)}')
        if isfile(eFileName):
            eFileFlag = True
        else:
            eFileFlag = False
        with open(eFileName, 'a', encoding='utf8') as f:
            if eFileFlag:
                f.write('\n')
            f.write(f'{station_code}\t{execution_time}\t{user_account}\t{uid}\t{executed_file}\t2\t{errors}')
        logger(f"Error data '{station_code}', {execution_time}, '{user_account}', {uid}, 2, {errors} saved locally in {eFileName}")

    finally:
        connection.close()
        logger('Connection closed. Sending error process ended.')

    logger(escapeMessage)
    from sys import exit
    exit()



''' Codes '''
if __name__ == "__main__":
    # Connect to Honeywell HPMA115S0-XXX 
    try:
        sensor = hw.Honeywell(port="/dev/serial0", baud=9600)
        logger('Connection to sensor established successfully')

    except Exception as e:
        msg = ('Sensor communication failed! ERROR: ' + str(e))
        logError(e, msg)

    syncTime()

    # Get datetime & pollution data from the sensor
    try:
        measured_time, pm10, pm25 = str(sensor.read()).split(',') # NOTE) measured_time returns GMT
        measured_time = datetime.now()
        logger(f'[DATA] measured_time: {measured_time}, PM10: {pm10}, PM25: {pm25}')

    except Exception as e:
        msg = 'Getting data from sensor failed. ERROR:' + str(e)
        logError(str(e), msg)


    try:
        connection, cursor = connectDB()

        station_code = getStationCode()

        mFileName = '/home/pi/raspmeasure/measurements.csv'
        mTableName = 'air_quality'
        mColumnList = ['station_code', 'measured_time', 'pm10', 'pm25']

        if isfile(mFileName):
            logger(f'Found previous measurements that could not be sent properly to DB server. Try again to save those...')
            measurementFile = pd.read_csv(mFileName, encoding='utf-8', names=mColumnList)
            measurementFile = measurementFile.astype({'station_code': 'str'})
            measurementFile['station_code'] = measurementFile['station_code'].apply(lambda x: '0'+str(x) if int(x) < 10 else x)
            measurementFile = list(measurementFile.values.tolist())
            query = f"INSERT INTO `{mTableName}` ({', '.join(mColumnList)}) VALUES (%s, %s, %s, %s);"
            cursor.executemany(query, measurementFile)
            connection.commit()
            if int(cursor.rowcount) > 1:
                messageVerb = 'were'
            else:
                messageVerb = 'was'
            logger('Previous', str(cursor.rowcount), 'measurement', messageVerb, 'inserted.')
            system(f'rm -rf {mFileName}')
            logger(f'{mFileName} deleted. Continue to next step!')
        query = f"INSERT INTO {mTableName} ({', '.join(mColumnList)}) VALUES ('{station_code}', '{measured_time}', {pm10}, {pm25});"
        cursor.execute(query)
        connection.commit()
        logger(f"'{station_code}', {measured_time}, {pm10}, {pm25} inserted.")

    except Exception as e:
        if isfile(mFileName):
            mFileFlag = True
        else:
            mFileFlag = False
        # Save measurement to local drive when error occurs
        with open(mFileName, 'a', encoding='utf-8') as f:
            if mFileFlag:
                f.write('\n')
            f.write(','.join([str(eval(col)) for col in mColumnList]))
        logger('Measurement data saved in locally for error while sending data')
        logError(e, 'Sending measurements failed! ERROR: ' + str(e))

    finally:
        connection.close()
        logger('Sending measurements process ended successfuly! Connection closed.')