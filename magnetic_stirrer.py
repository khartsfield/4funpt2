import atexit
import time
import logging
import threading
import random
from ftdi_serial import Serial
from hein_utilities.runnable import Runnable
from ika.temporal_data import *
from ika.errors import IKAError
from ika.utilities import stable_against_known

# todo add errors

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class MagneticStirrer(Runnable):
    """
    Establish a connection with an IKA magnetic stirrer
    Supported models:
        - C-MAG HS 7
        - RCT 5 digital

    Not inherent in the IKA hot plate, is the ability to wait and know when the temperature has stabilized. A custom
    way to know has been added, see the wait_until_temperature_stable function.

    Parameters for knowing when the temperature has stabilized
        :int, n: the number of most recent measurements used to determine if the temperature has been stabilized
        :float, std_max: maximum standard deviation the data can have to be determined as stable
        :float, sem_max: maximum standard error the data can have to be determined as stable
        :bool, relative_limits: if true, then the upper and lower limits, if their values are 0 < 1,
            will be relative to the range of all temperature measurements so far
        :float, upper_limit: if relative limits is False, it is the absolute temperature (C) that the mean
            and mode of the data can is allowed to be above than the plate target temperature, to determine if it
            has stabilized.
            if the value is above 0 and less than 1 and relative limits is True,  it is the percent of the range of all
            the temperature data gathered so far (range = max - min values) that will be converted into absolute
            temperature for use in this function
        :float, lower_limit: if relative limits is False, it is the absolute temperature (C) that the mean
            and mode of the data can is allowed to be below than the plate target temperature, to determine if it
            has stabilized.
            if the value is above 0 and less than 1 and relative limits is True,  it is the percent of the range of all
            the temperature data gathered so far (range = max - min values) that will be converted into absolute
            temperature for use in this function
        :float, r_min: minimum r when doing a linear regression on the data required for the data =to be
            determined as stable
        :float, slope_upper_limit: how much above zero the slope from doing a linear regression can be in order for
            the data to be determined as stable
        :float, slope_lower_limit: how much below zero the slope from doing a linear regression can be in order for
            the data to be determined as stable
    """

    # hex command characters for data transmission
    SP_HEX = "\x20"  # space or blank
    CR_HEX = "\x0d"  # carriage return
    LF_HEX = "\x0a"  # line feed or new line
    DOT_HEX = "\x2E"  # dot
    LINE_ENDING = CR_HEX + LF_HEX  # each individual command and each response are terminated CR LF
    LINE_ENDING_ENCODED = LINE_ENDING.encode()

    # default connection parameters
    CONNECTION_SETTINGS = dict(
        baudrate=9600,
        data_bits=Serial.DATA_BITS_7,
        stop_bits=Serial.STOP_BITS_1,  # todo check with someone because it seems like this is 0 even if it is called 1
        parity=Serial.PARITY_EVEN,
    )

    # constant names are the functions, and the values are the corresponding NAMUR commands
    READ_THE_DEVICE_NAME = "IN_NAME"
    READ_ACTUAL_EXTERNAL_SENSOR_VALUE = "IN_PV_1"
    READ_ACTUAL_HOTPLATE_SENSOR_VALUE = "IN_PV_2"
    READ_STIRRING_SPEED_VALUE = "IN_PV_4"
    READ_VISCOSITY_TREND_VALUE = "IN_PV_5"
    READ_RATED_TEMPERATURE_VALUE = "IN_SP_1"
    READ_RATED_SET_SAFETY_TEMPERATURE_VALUE = "IN_SP_3"  # find the set safe temperature of the plate, the target/set
    # temperature the plate can go to is 50 degrees beneath this
    READ_RATED_SPEED_VALUE = "IN_SP_4"
    ADJUST_THE_SET_TEMPERATURE_VALUE = "OUT_SP_1"
    SET_TEMPERATURE_VALUE = "OUT_SP_1 "  # requires a value to be appended to the end of the command
    ADJUST_THE_SET_SPEED_VALUE = "OUT_SP_4"
    SET_SPEED_VALUE = "OUT_SP_4 "  # requires a value to be appended to the end of the command
    START_THE_HEATER = "START_1"
    STOP_THE_HEATER = "STOP_1"
    START_THE_MOTOR = "START_4"
    STOP_THE_MOTOR = "STOP_4"
    SWITCH_TO_NORMAL_OPERATING_MODE = "RESET"
    SET_OPERATING_MODE_A = "SET_MODE_A"
    SET_OPERATING_MODE_B = "SET_MODE_B"
    SET_OPERATING_MODE_D = "SET_MODE_D"
    SET_WD_SAFETY_LIMIT_TEMPERATURE_WITH_SET_VALUE_ECHO = "OUT_SP_12@"  # requires a value to be appended to the end of
    # the command
    SET_WD_SAFETY_LIMIT_SPEED_WITH_SET_VALUE_ECHO = "OUT_SP_12@"  # requires a value to be appended to the end of
    # the command
    WATCHDOG_MODE_1 = "OUT_WD1@"   # requires a value (bw 20-1500) to be appended to the end of the command - this is
    # the watchdog time in seconds. this command launches the watchdog function and must be transmitted within the
    # set watchdog time. in watchdog mode 1, if event WD1 occurs, the heating and stirring functions are switched off
    #  and ER 2 is displayed
    WATCHDOG_MODE_2 = "OUT_WD2@"   # requires a value (bw 20-1500) to be appended to the end of the command - this is
    # the watchdog time in seconds. this command launches the watchdog function and must be transmitted within the
    # set watchdog time. the WD2 event can be reset with the command "OUT_WD2@0", and this also stops the watchdog
    # function.  in watchdog mode 2, if event WD2 occurs, the speed target value is changed to the WD safety speed
    # limit and the temperature target value is change to the WD safety temperature limit value

    human_readable_commands: Dict[str, str] = {
        ADJUST_THE_SET_TEMPERATURE_VALUE: 'adjust the set temperature value',
        SET_TEMPERATURE_VALUE: 'set target temperature',
        ADJUST_THE_SET_SPEED_VALUE: 'adjust the set stir rate value',
        SET_SPEED_VALUE: 'set target stir rate',
        START_THE_HEATER: 'start heating',
        STOP_THE_HEATER: 'stop heating',
        START_THE_MOTOR: 'start stirring',
        STOP_THE_MOTOR: 'stop stirring',
        SWITCH_TO_NORMAL_OPERATING_MODE: 'switch to normal operating mode',
        SET_OPERATING_MODE_A: 'set operating mode a',
        SET_OPERATING_MODE_B: 'set operating mode b',
        SET_OPERATING_MODE_D: 'set operating mode d',
    }

    probe_temperature_column_heading = 'Probe temperature (C)'
    plate_surface_temperature_column_heading = 'Plate surface temperature (C)'
    target_temperature_column_heading = 'Target temperature (C)'
    stir_rate_column_heading = 'Stir rate (rpm)'
    target_stir_rate_column_heading = 'Target stir rate (rpm)'
    command_column_heading = 'Command'

    def __init__(self,
                 device_port: str,
                 save_path: Path = None,
                 datetime_format: str = '%Y_%m_%d_%H_%M_%S',
                 safe_connect: bool = True,
                 ):
        """

        :param device_port: port on computer to connect to the hotplate. For example, 'COM3'
        :param save_path: path of where to save the data files to. The file names will be appended with either
            'state_data' or 'control_data', as 2 csv files are generated
        :param str, datetime_format: string format for the time stamps
        :param bool, safe_connect: whether or not to stop heating and stirring on connection or not
        """
        Runnable.__init__(self, logger=logger)
        self.ser: Serial = None
        self._lock = threading.Lock()
        self._device_port = device_port
        self._heating: bool = None
        self._stirring: bool = None
        self._datetime_format = datetime_format

        self.datetime_manager_rounding = 4

        self.connect()

        self.state_data: TemporalData = TemporalData()
        self.state_data.datetime_format = self.datetime_format
        self.command_data: TemporalData = TemporalData()
        self.command_data.datetime_format = self.datetime_format

        self._save_path: Path = None
        self.save_path = save_path
        self.set_up_data()

        self._record_data_interval: int = 1
        self.save_state_data_interval = 1  # interval of number of data points to save the temperature csv file
        self.set_temperatures: List[float] = []  # list of the temperatures to go to

        self.safe_connect = safe_connect
        if safe_connect:
            self.stop_stirring()
            self.stop_heating()
        self._safe_disconnect = True
        """
        Parameters for knowing when the temperature has stabilized
        :param n: the number of most recent measurements used to determine if the temperature has been stabilized
        :param float, std_max: maximum standard deviation the data can have to be determined as stable
        :param float, sem_max: maximum standard error the data can have to be determined as stable
        :param bool, relative_limits: if true, then the upper and lower limits, if their values are 0 < 1, 
            will be relative to the range of all temperature measurements so far 
        :param float, upper_limit: if relative limits is False, it is the absolute temperature (C) that the mean 
            and mode of the data can is allowed to be above than the plate target temperature, to determine if it 
            has stabilized. 
            if the value is above 0 and less than 1 and relative limits is True,  it is the percent of the range of all 
            the temperature data gathered so far (range = max - min values) that will be converted into absolute 
            temperature for use in this function
        :param float, lower_limit: if relative limits is False, it is the absolute temperature (C) that the mean 
            and mode of the data can is allowed to be below than the plate target temperature, to determine if it 
            has stabilized. 
            if the value is above 0 and less than 1 and relative limits is True,  it is the percent of the range of all 
            the temperature data gathered so far (range = max - min values) that will be converted into absolute 
            temperature for use in this function
        :param float, r_min: minimum r when doing a linear regression on the data required for the data =to be
            determined as stable
        :param float, slope_upper_limit: how much above zero the slope from doing a linear regression can be in order for
            the data to be determined as stable
        :param float, slope_lower_limit: how much below zero the slope from doing a linear regression can be in order for
            the data to be determined as stable
        """
        self._n: int = 120
        self._std_max: float = 0.05
        self._sem_max: float = 0.05
        self._relative_limits: bool = False
        self._upper_limit: float = 1
        self._lower_limit: float = 1
        self._r_min: float = None
        self._slope_upper_limit: float = None
        self._slope_lower_limit: float = None

    @property
    def datetime_format(self) -> str:
        return self._datetime_format

    @datetime_format.setter
    def datetime_format(self,
                        value: str):
        logger.info('datetime format cannot be set after instance has been instantiated')

    @property
    def save_path(self) -> Path:
        return self._save_path

    @save_path.setter
    def save_path(self,
                  value: Path):
        self._save_path = value if value is not None else Path.cwd().joinpath('ika')
        file_name = self._save_path.name
        state_path = self.save_path.with_name(f'{file_name}_state_data')
        command_path = self.save_path.with_name(f'{file_name}_command_data')
        self.state_data.save_path = state_path
        self.command_data.save_path = command_path
        # change the save path if a file with that name already exists
        index = 1
        while self.state_data.save_path.exists():
            self._save_path = self._save_path.parent.joinpath(f'{file_name}_copy_{index}')
            new_file_name = self._save_path.name
            state_path = self._save_path.with_name(f'{new_file_name}_state_data')
            command_path = self._save_path.with_name(f'{new_file_name}_command_data')
            index += 1
            self.state_data.save_path = state_path
            self.command_data.save_path = command_path

    @property
    def heating(self) -> bool:
        """ true if hot plate is heating; used for tracking, does not control the plat"""
        return self._heating

    @heating.setter
    def heating(self, value):
        self._heating = value

    @property
    def stirring(self) -> bool:
        """ true if hot plate is stirring; used for tracking, does not control the plat"""
        return self._stirring

    @stirring.setter
    def stirring(self, value):
        self._stirring = value

    @property
    def stir_rate(self) -> float:
        """
        Plate actual stir rate

        :return:
        """
        return self.read_stirring_speed_value()

    @property
    def target_stir_rate(self) -> float:
        """
        Stir rate hotplate is set to go to

        :return:
        """
        return self.read_rated_speed_value()

    @target_stir_rate.setter
    def target_stir_rate(self,
                         value,
                         ):
        self.set_speed_value(value=value)

    def set_target_stir_rate(self,
                             value,
                             ):
        self.target_stir_rate = value

    @property
    def probe_temperature(self):
        """
        The temperature (degrees C) picked up by the temperature probe

        :return:
        """
        return self.read_actual_external_sensor_value()

    @property
    def target_temperature(self) -> float:
        """
        Temperature hotplate is set to go to

        :return:
        """
        return self.read_rated_temperature_value()

    @target_temperature.setter
    def target_temperature(self,
                           value,
                           ):
        self.set_temperature_value(value=value)

    def set_target_temperature(self,
                               value,
                               ):
        self.target_temperature = value

    @property
    def hotplate_sensor_temperature(self) -> float:
        """
        The value (degrees C) that the hotplate itself is at

        :return:
        """
        return self.read_actual_hotplate_sensor_value()

    @property
    def hardware_safety_temperature(self):
        return self.read_rated_set_safety_temperature_value()

    @property
    def viscosity_trend(self):
        """
        The viscosity trend

        :return:
        """
        return self.read_viscosity_trend_value()

    @property
    def safe_disconnect(self) -> bool:
        return self._safe_disconnect

    @safe_disconnect.setter
    def safe_disconnect(self, value):
        self._safe_disconnect = value

    @property
    def n(self) -> int:
        return self._n

    @n.setter
    def n(self,
          value: int,
          ):
        if isinstance(value, int) is False:
            raise TypeError('value must be of type int')
        self._n = value

    @property
    def std_max(self) -> float:
        return self._std_max

    @std_max.setter
    def std_max(self,
                value: float,
                ):
        self._std_max = value

    @property
    def sem_max(self) -> float:
        return self._sem_max

    @sem_max.setter
    def sem_max(self,
                value: float,
                ):
        self._sem_max = value

    @property
    def upper_limit(self) -> float:
        return self._upper_limit

    @upper_limit.setter
    def upper_limit(self,
                    value: float,
                    ):
        self._upper_limit = value

    @property
    def lower_limit(self) -> float:
        return self._lower_limit

    @lower_limit.setter
    def lower_limit(self,
                    value: float,
                    ):
        self._lower_limit = value

    @property
    def relative_limits(self) -> bool:
        return self._relative_limits

    @relative_limits.setter
    def relative_limits(self,
                        value: bool,
                        ):
        self._relative_limits = value

    @property
    def r_min(self) -> float:
        return self._r_min

    @r_min.setter
    def r_min(self,
              value: float,
              ):
        self._r_min = value

    @property
    def slope_upper_limit(self) -> float:
        return self._slope_upper_limit

    @slope_upper_limit.setter
    def slope_upper_limit(self,
                          value: float,
                          ):
        self._slope_upper_limit = value

    @property
    def slope_lower_limit(self) -> float:
        return self._slope_lower_limit

    @slope_lower_limit.setter
    def slope_lower_limit(self,
                          value: float,
                          ):
        self._slope_lower_limit = value

    @property
    def record_data_interval(self):
        """minimum number of seconds in between recording data points for self.state_data"""
        return self._record_data_interval

    @record_data_interval.setter
    def record_data_interval(self, value):
        self._record_data_interval = value

    def connect(self):
        try:
            if self.ser is None:
                cn = Serial(device_port=self._device_port,
                            **self.CONNECTION_SETTINGS,
                            )
                self.ser = cn
            else:
                self.ser.connect()

            logger.info(self.read_device_name())
            # Ensure that the serial port is closed on system exit
            atexit.register(self.disconnect)
        except Exception as e:
            logger.warning("could not connect")
            raise IKAError(msg='Could not connect to the plate, make sure the right port was selected')

    def disconnect(self):
        """
        Stop heating and stirring and close the serial port

        :return:
        """
        try:
            if self.safe_disconnect:
                self.stop_the_heater()
                self.stop_the_motor()
            # disconnect
            self.ser.disconnect()
        except Exception as e:
            logger.warning("could not disconnect")
            raise IKAError(msg='Could not disconnect from plate')

    def set_up_data(self):
        start_time: str = now_string(self.datetime_format)
        self.set_up_state_data(start_time=start_time)
        self.set_up_command_data(start_time=start_time)

    def set_up_state_data(self, start_time) -> None:
        """
        For the Time column, what's in the parenthesis is the datetime format set, and the values are strings,
        but for the rest, the values are floats or datetime objects

        Example table:

        +-----------------------------+----------+------------+-------------+-----------------------+---------------------------------+------------------------+-----------------+--------------------------+
        | Time (self.datetime_format) | Time (s) | Time (min) | Time (hour) | Probe temperature (C) | Plate surface   temperature (C) | Target temperature (C) | Stir rate (rpm) | Target stir rate   (rpm) |
        +-----------------------------+----------+------------+-------------+-----------------------+---------------------------------+------------------------+-----------------+--------------------------+
        |          datetime_1         |     0    |      0     |      0      |          pt1          |               pst1              |           tt1          |       sr1       |           tsr1           |
        +-----------------------------+----------+------------+-------------+-----------------------+---------------------------------+------------------------+-----------------+--------------------------+
        |          datetime_2         |    30    |     0.5    |    0.0083   |          pt2          |               pst2              |           tt2          |       sr2       |           tsr2           |
        +-----------------------------+----------+------------+-------------+-----------------------+---------------------------------+------------------------+-----------------+--------------------------+
        |          datetime_3         |    60    |      1     |    0.0167   |          pt3          |               pst3              |           tt3          |       sr3       |           tsr3           |
        +-----------------------------+----------+------------+-------------+-----------------------+---------------------------------+------------------------+-----------------+--------------------------+

        :return: None
        """
        probe_temperature = self.probe_temperature
        plate_surface_temperature = self.hotplate_sensor_temperature
        target_temperature = self.target_temperature
        stir_rate = self.stir_rate
        target_stir_rate = self.target_stir_rate
        add_data = {self.probe_temperature_column_heading: probe_temperature,
                    self.plate_surface_temperature_column_heading: plate_surface_temperature,
                    self.target_temperature_column_heading: target_temperature,
                    self.stir_rate_column_heading: stir_rate,
                    self.target_stir_rate_column_heading: target_stir_rate,
                    }
        self.state_data.add_data(add_data, t=start_time)

    def set_up_command_data(self, start_time) -> None:
        """
        For the Time column, what's in the parenthesis is the datetime format set, and the values are strings,
        but for the rest of the time columns, the values are floats

        In the command column, put select commands that are through Python to the hot plate in human readable form

        Example table:

        +-----------------------------+----------+------------+-------------+-----------+
        | Time (self.datetime_format) | Time (s) | Time (min) | Time (hour) |  Command  |
        +-----------------------------+----------+------------+-------------+-----------+
        |          datetime_1         |     0    |      0     |      0      |   START   |
        +-----------------------------+----------+------------+-------------+-----------+
        |          datetime_2         |    30    |     0.5    |    0.0083   | COMMAND_2 |
        +-----------------------------+----------+------------+-------------+-----------+
        |          datetime_3         |    60    |      1     |    0.0167   | COMMAND_3 |
        +-----------------------------+----------+------------+-------------+-----------+

        :return: None
        """
        add_data = {self.command_column_heading: 'START',
                    }
        self.command_data.add_data(add_data, start_time)

    def save_csv_files(self):
        self.state_data.save_csv()
        self.command_data.save_csv()

    def register_state(self) -> None:
        probe_temperature = self.probe_temperature
        plate_surface_temperature = self.hotplate_sensor_temperature
        target_temperature = self.target_temperature
        stir_rate = self.stir_rate
        target_stir_rate = self.target_stir_rate
        add_data = {self.probe_temperature_column_heading: probe_temperature,
                    self.plate_surface_temperature_column_heading: plate_surface_temperature,
                    self.target_temperature_column_heading: target_temperature,
                    self.stir_rate_column_heading: stir_rate,
                    self.target_stir_rate_column_heading: target_stir_rate,
                    }
        self.state_data.add_data(add_data)
        nrows = len(self.state_data.data)
        if nrows % self.save_state_data_interval == 0:
            self.state_data.save_csv()

    def register_command(self, command: str) -> None:
        add_data = {self.command_column_heading: command}
        self.command_data.add_data(add_data)
        self.command_data.save_csv()

    def run(self):
        """function to monitor temperature in the background every second\
        """
        while self.running:
            time.sleep(self.record_data_interval)
            self.register_state()

    def start_background_monitoring(self):
        """start the thread to monitor temperature in the background every second"""
        self.start()

    def stop_background_monitoring(self):
        """stop the thread to monitor temperature in the background every second"""
        self.stop()

    def stable(self,
               x,
               y,
               ) -> bool:
        """
        Definition of stability:
        Check if the temperature measurements mean and mode fall within set temperature value plus/minus the
        lower_limit and upper limits, and if the standard deviation is less than std_max, and the standard error is
        less than sem_max, and if the r value from doing a linear regression is less than r_min and the slope from
        doing a linear regression is plus/minus slope upper and lower limits.

        All of the properties that are used in this function must have been set beforehand

        :param x: 1d array of the x data; time data
        :param y: 1d array of the y data; temperature data

        :return: True if based on the data passed in, the temperature has stabilized to the temperature the hot plate
            was set to go to
        """
        temperatures = self.state_data.data[self.probe_temperature_column_heading].tolist()
        y_max = max(temperatures)
        y_min = min(temperatures)
        total_range = y_max - y_min
        if self.upper_limit < 1 and self.relative_limits is True:
            upper_limit = self.upper_limit * total_range
        else:
            upper_limit = self.upper_limit
        if self.lower_limit < 1 and self.relative_limits is True:
            lower_limit = self.lower_limit * total_range
        else:
            lower_limit = self.lower_limit

        stable: bool = stable_against_known(x=x,
                                            y=y,
                                            known=self.target_temperature,
                                            upper_limit=upper_limit,
                                            lower_limit=lower_limit,
                                            std_max=self.std_max,
                                            sem_max=self.sem_max,
                                            r_min=self.r_min,
                                            slope_upper_limit=self.slope_upper_limit,
                                            slope_lower_limit=self.slope_lower_limit,
                                            )
        return stable

    def wait_until_temperature_stable(self,
                                      time_out: float = 1800,
                                      ) -> bool:
        """
        Check for when the temperature has stabilized, and pause code execution until this happens or when
        timeout number of seconds has passed. Every measurement takes about 1 second.

        :param float, time_out: every measurement takes self.record_data_interval seconds. The time_out value is the
            maximum number seconds after this function has been started that it can run for until it must return.
            This is to prevent the function from holding something up for too long

        :return:
        """
        n = self.n
        start_time: datetime = datetime.now()
        was_running = self.running  # if currently data logging in the background
        if was_running:
            self.stop_background_monitoring()
        while True:
            current_time: datetime = datetime.now()
            seconds_passed: float = (current_time - start_time).seconds

            if seconds_passed > time_out:
                if was_running:
                    self.start_background_monitoring()
                return False
            else:
                time.sleep(self.record_data_interval)
                self.register_state()
                last_n_times = self.state_data.tail(n, self.state_data.time_s_column_heading)
                last_n_temperatures = self.state_data.tail(n, self.probe_temperature_column_heading)
                if len(last_n_times) < n:
                    continue
                else:
                    stable = self.stable(
                        x=last_n_times,
                        y=last_n_temperatures,
                    )
                    if stable:
                        if was_running:
                            self.start_background_monitoring()
                        return True
                    else:
                        continue

    def _send_and_receive(self,
                          command: str,
                          ):
        """
        Send a command, get a response back, and return the response
        :param str, command: a command that will give back a response - these will be:
            READ_THE_DEVICE_NAME
            READ_ACTUAL_EXTERNAL_SENSOR_VALUE
            READ_ACTUAL_HOTPLATE_SENSOR_VALUE
            READ_STIRRING_SPEED_VALUE
            READ_VISCOSITY_TREND_VALUE
            READ_RATED_TEMPERATURE_VALUE
            READ_RATE_SET_SAFETY_TEMPERATURE_VALUE
            READ_RATE_SPEED_VALUE

        :return:
        """
        with self._lock:
            # format the command to send so that it terminates with the line ending (CR LF)
            formatted_command: str = command + self.LINE_ENDING
            formatted_command_encoded = formatted_command.encode()
            # this is the response, and is returned
            return_string = self.ser.request(data=formatted_command_encoded,
                                             line_ending=self.LINE_ENDING_ENCODED,
                                             ).decode()
            # all the functions that would use this function, except when asking for the device name, returns a number.
            # however the return string type for all the other functions is a string of the type '#.# #', so we want to
            # change that into a float instead so it can be easily used
            if return_string == 'C-MAG HS7':
                return 'C-MAG HS7'
            elif return_string == 'RCT digital':
                return 'RCT digital'
            else:
                formatted_return_float = float(return_string.split()[0])  # return just the information we want as a float
            return formatted_return_float

    def _send(self,
              command: str,
              ):
        """
        Send a command
        :param str, command: a command with optional parameter's included if required (such as for setting temperature
            or stirring rate

        :return:
        """
        with self._lock:
            # format the command to send so that it terminates with the line ending (CR LF)
            formatted_command: str = command + self.LINE_ENDING
            formatted_command_encoded = formatted_command.encode()
            self.ser.write(data=formatted_command_encoded)  # commands need to be encoded when sent

    def read_device_name(self):
        return self._send_and_receive(command=self.READ_THE_DEVICE_NAME)

    def read_actual_external_sensor_value(self):
        """
        read and return the temperature (degrees C) picked up by the temperature probe

        :return:
        """
        return self._send_and_receive(command=self.READ_ACTUAL_EXTERNAL_SENSOR_VALUE)

    def read_actual_hotplate_sensor_value(self):
        """
        read and return the value (degrees C) that the hotplate itself is at

        :return:
        """
        return self._send_and_receive(command=self.READ_ACTUAL_HOTPLATE_SENSOR_VALUE)

    def read_stirring_speed_value(self):
        return self._send_and_receive(command=self.READ_STIRRING_SPEED_VALUE)

    def read_viscosity_trend_value(self):
        return self._send_and_receive(command=self.READ_VISCOSITY_TREND_VALUE)

    def read_rated_temperature_value(self):
        """
        read and return the temperature (degrees C) that the hotplate was set to maintain

        :return:
        """
        return self._send_and_receive(command=self.READ_RATED_TEMPERATURE_VALUE)

    def read_rated_set_safety_temperature_value(self):
        return self._send_and_receive(command=self.READ_RATED_SET_SAFETY_TEMPERATURE_VALUE)

    def read_rated_speed_value(self):
        return self._send_and_receive(command=self.READ_RATED_SPEED_VALUE)

    def adjust_the_set_temperature_value(self):
        self._send(command=self.ADJUST_THE_SET_TEMPERATURE_VALUE)

    def set_temperature_value(self,
                              value,
                              ):
        command = self.SET_TEMPERATURE_VALUE + str(value) + ' '
        self._send(command=command)
        command_str = self.human_readable_commands[self.SET_TEMPERATURE_VALUE] + f' to {str(value)}'
        self.register_command(command_str)
        self.set_temperatures.append(value)

    def adjust_the_set_speed_value(self):
        self._send(command=self.ADJUST_THE_SET_SPEED_VALUE)

    def set_speed_value(self,
                        value,
                        ):
        command = self.SET_SPEED_VALUE + str(value) + ' '
        self._send(command=command)
        command_str = self.human_readable_commands[self.SET_SPEED_VALUE] + f' to {str(value)}'
        self.register_command(command_str)

    def start_the_heater(self):
        self._send(command=self.START_THE_HEATER)
        self.heating = True
        command_str = self.human_readable_commands[self.START_THE_HEATER]
        self.register_command(command_str)

    def start_heating(self):
        self.start_the_heater()

    def stop_the_heater(self):
        self._send(command=self.STOP_THE_HEATER)
        self.heating = False
        command_str = self.human_readable_commands[self.STOP_THE_HEATER]
        self.register_command(command_str)

    def stop_heating(self):
        self.stop_the_heater()

    def start_the_motor(self):
        self._send(command=self.START_THE_MOTOR)
        self.stirring = True
        command_str = self.human_readable_commands[self.START_THE_MOTOR]
        self.register_command(command_str)

    def start_stirring(self):
        self.start_the_motor()

    def stop_the_motor(self):
        self._send(command=self.STOP_THE_MOTOR)
        self.stirring = False
        command_str = self.human_readable_commands[self.STOP_THE_MOTOR]
        self.register_command(command_str)

    def stop_stirring(self):
        self.stop_the_motor()

    def switch_to_normal_operating_mode(self):
        self._send(command=self.SWITCH_TO_NORMAL_OPERATING_MODE)
        command_str = self.human_readable_commands[self.SWITCH_TO_NORMAL_OPERATING_MODE]
        self.register_command(command_str)

    def set_operating_mode_a(self):
        self._send(command=self.SET_OPERATING_MODE_A)
        command_str = self.human_readable_commands[self.SET_OPERATING_MODE_A]
        self.register_command(command_str)

    def set_operating_mode_b(self):
        self._send(command=self.SET_OPERATING_MODE_B)
        command_str = self.human_readable_commands[self.SET_OPERATING_MODE_B]
        self.register_command(command_str)

    def set_operating_mode_d(self):
        self._send(command=self.SET_OPERATING_MODE_D)
        command_str = self.human_readable_commands[self.SET_OPERATING_MODE_D]
        self.register_command(command_str)

    def set_wd_safety_limit_temperature(self,
                                        value: str,
                                        ):
        command = self.SET_WD_SAFETY_LIMIT_TEMPERATURE_WITH_SET_VALUE_ECHO + value + ' '
        return self._send_and_receive(command=command)

    def set_wd_safety_limit_speed(self,
                                  value,
                                  ):
        command = self.SET_WD_SAFETY_LIMIT_SPEED_WITH_SET_VALUE_ECHO + str(value) + ' '
        return self._send_and_receive(command=command)

    def watchdog_mode_1(self,
                        value,
                        ):
        """
        This command launches the watchdog function and must be transmitted within the set watchdog time.
        in watchdog mode 1, if event WD1 occurs, the heating and stirring functions are switched off and ER 2 is
        displayed

        :param value: value between 20 and 1500 (units in seconds) - the watchdog time

        :return:
        """
        command = self.WATCHDOG_MODE_1 + str(value) + ' '
        self._send(command=command)

    def watchdog_mode_2(self,
                        value: str,
                        ):
        """
        This command launches the watchdog function and must be transmitted within the set watchdog time. the WD2
        event can be reset with the command "OUT_WD2@0", and this also stops the watchdog function.  in watchdog mode
        2, if event WD2 occurs, the speed target value is changed to the WD safety speed limit and the temperature
        target value is change to the WD safety temperature limit value

        :param value: value between 20 and 1500 (units in seconds) - the watchdog time

        :return:
        """
        command = self.WATCHDOG_MODE_2 + value + ' '
        self._send(command=command)


class MockMagneticStirrer(MagneticStirrer):
    """
    A mock class of the magnetic stirrer class to test things out without having to connect to one. All commands
    will now instead log
    """

    def __init__(self):
        logger.debug(f'created a mock IKA magnetic stirrer')

        self.heating: bool = False  # true if hot plate is heating
        self.stirring: bool = False  # true if hot plate is heating

    def wait_until_temperature_stabilized(self):
        logger.debug('wait_until_temperature_stabilized')

    def read_device_name(self):
        logger.debug(f'read device name command sent, get back a string')

    def read_actual_external_sensor_value(self):
        logger.debug(f'read actual external sensor value command sent, get back a number')
        return random.randint(20, 25)

    def read_actual_hotplate_sensor_value(self):
        logger.debug(f'read actual hotplate sensor command sent, got back a number')
        return random.randint(20, 25)

    def read_stirring_speed_value(self):
        logger.debug(f'read stirring speed value command sent, got back a number')
        return random.randint(20, 25)

    def read_viscosity_trend_value(self):
        logger.debug(f'read viscosity trend value command sent, got back a number')
        return random.randint(20, 25)

    def read_rated_temperature_value(self):
        logger.debug(f'read rated temperature value command sent, got back a number')
        return random.randint(20, 25)

    def read_rated_set_safety_temperature_value(self):
        logger.debug(f'read rate set safety temperature value command sent, got back a number')
        return random.randint(20, 25)

    def read_rated_speed_value(self):
        logger.debug(f'read rate speed value command sent, got back a number')
        return random.randint(20, 25)

    def adjust_the_set_temperature_value(self):
        logger.debug(f'adjust the set temperature value command sent')

    def set_temperature_value(self,
                              value,
                              ):
        logger.debug(f'set temperature value to {value} command sent')

    def adjust_the_set_speed_value(self):
        logger.debug(f'adjust the set speed value command sent')

    def set_speed_value(self,
                        value,
                        ):
        logger.debug(f'set speed to {value} value command sent')

    def start_the_heater(self):
        logger.debug(f'start the heater command sent')
        self.heating = True

    def stop_the_heater(self):
        logger.debug(f'stop the heater command sent')
        self.heating = False

    def start_the_motor(self):
        logger.debug(f'start the motor command sent')
        self.stirring = True

    def stop_the_motor(self):
        logger.debug(f'stop the motor command sent')
        self.stirring = False

    def switch_to_normal_operating_mode(self):
        logger.debug(f'switch to normal operating mode command sent')

    def set_operating_mode_a(self):
        logger.debug(f'switch to a operating mode command sent')

    def set_operating_mode_b(self):
        logger.debug(f'switch to b operating mode command sent')

    def set_operating_mode_d(self):
        logger.debug(f'switch to d operating mode command sent')

    def set_wd_safety_limit_temperature(self,
                                        value: str,
                                        ):
        logger.debug(f'set wd safety limit temperature to {value} command sent')

    def set_wd_safety_limit_speed(self,
                                  value,
                                  ):
        logger.debug(f'set wd safety limit speed to {value} command sent')

    def watchdog_mode_1(self,
                        value,
                        ):
        """
        This command launches the watchdog function and must be transmitted within the set watchdog time.
        in watchdog mode 1, if event WD1 occurs, the heating and stirring functions are switched off and ER 2 is
        displayed

        :param value: value between 20 and 1500 (units in seconds) - the watchdog time

        :return:
        """
        logger.debug(f'set watchdog mode 1 with value {value} command sent')

    def watchdog_mode_2(self,
                        value: str,
                        ):
        """
        This command launches the watchdog function and must be transmitted within the set watchdog time. the WD2
        event can be reset with the command "OUT_WD2@0", and this also stops the watchdog function.  in watchdog mode
        2, if event WD2 occurs, the speed target value is changed to the WD safety speed limit and the temperature
        target value is change to the WD safety temperature limit value

        :param value: value between 20 and 1500 (units in seconds) - the watchdog time

        :return:
        """
        logger.debug(f'set watchdog mode 2 with value {value} command sent')


