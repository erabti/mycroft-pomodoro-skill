# Copyright 2016 Mycroft AI, Inc.
#
# This file is part of Mycroft Core.
#
# Mycroft Core is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Mycroft Core is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Mycroft Core.  If not, see <http://www.gnu.org/licenses/>.

from mycroft.skills.core import MycroftSkill
from mycroft.util.log import getLogger
from adapt.intent import IntentBuilder
from datetime import datetime, timedelta
import dateutil.parser as dparser

__author__ = 'erabti'

LOGGER = getLogger(__name__)


def parse_to_datetime(duration, timeleft=False):
    """ Takes in duration and output datetime

        Args:
            duration (str): string in any time format
                            ex. 1 hour 2 minutes 30 seconds

        Return:
            timer_time (datetime): datetime object with
                                   time now + duration
    """
    parsed_time = dparser.parse(duration, fuzzy=True)
    now = datetime.now()

    seconds = parsed_time.second
    minutes = parsed_time.minute
    hours = parsed_time.hour

    timer_time = now + timedelta(hours=hours, minutes=minutes, seconds=seconds)
    time_left = timedelta(hours=hours, minutes=minutes, seconds=seconds)
    if timeleft:
        return time_left
    else:
        return timer_time


def get_time_human(time_left, timer_name="", timeleft=False):
    """ Turn into params into a string for status of timer

        Args:
            time_left (int): seconds
            timer_name (str): name of timer
            tiemleft (bool): whether to put it in time left format or not
        Return
            speak_string (str): timer string mycroft can speak

    """
    days = time_left // 86400
    hours = time_left // 3600 % 24
    minutes = time_left // 60 % 60
    seconds = time_left % 60
    speak_string = "There is " if timeleft else ""
    if days > 0:
        time_string = "day" if days == 1 else "days"
        speak_string += "{} {} ".format(days, time_string)
    if hours > 0:
        time_string = "hour" if hours == 1 else "hours"
        speak_string += "{} {} ".format(hours, time_string)
    if minutes > 0:
        time_string = "minute" if minutes == 1 else "minutes"
        speak_string += "{} {} ".format(minutes, time_string)
    if seconds > 0:
        time_string = "second" if seconds == 1 else "seconds"
        speak_string += "{} {}".format(seconds, time_string)
    if days == 0 and hours == 0 and minutes == 0 and seconds == 0:
        speak_string = "There is 0 seconds" if timeleft else "0 seconds"
    speak_string += "left on the {} timer".format(timer_name) if timeleft else ""

    return speak_string


def get_sec(time_string):
    h, m, s = str(time_string).split(':')
    return int(h) * 3600 + int(m) * 60 + int(s)


class PomodoroSkill(MycroftSkill):
        def __init__(self):
            super(PomodoroSkill, self).__init__(name='PomodoroSkill')
            self.cycles = 0   # number of pomodoros have been done
            self.runs = 0   # number of 4 pomodoro sessions been done
            self.work_duration = "25 minutes"   # default work duration
            self.break_duration = "5 minutes"   # default break duration
            self.long_break_duration = "15 minutes"   # default long break duration
            self.long_break_frequency = 4   # default long break frequency
            self.record = {'breaknum': 0, 'worknum': 0}  # keeps a record of break numbers and work numbers
            self.isworking = False  # checks if pomodoro events are running or canceled
            self.timetype = 'work'  # current work time

        def initialize(self):
            self.register_intent_file('start.pomodoro.intent', self.handle_start_intent)  # sentences used to start pomodoro
            self.register_intent_file('get.status.intent', self.handle_status_intent)  # sentences used to get status
            self.register_entity_file('workduration.entity')  # work duration wild card format
            self.register_entity_file('breakduration.entity')  # break duration wild card format
            stop_intent = IntentBuilder("StopMySkillIntent").require("StopPomodoroKeyword").build()
            self.register_intent(stop_intent, self.handle_stop)

        def handle_start_intent(self, message):
            self.cycles = 0  # cycle: after long_break_frequency
            self.process_pomodoro_inputs(message)  # assign new work and break durations if stated by user
            self.work_time()  # start looping

        def handle_status_intent(self, message):
            if self.isworking:  # checking if we're working or not
                duration = self.get_timeleft()  # cuurent timeleft
                next_timetype = 'break'  # the next time type, default is break
                current_timetype = self.timetype  # the current time type
                if current_timetype == 'break':
                    next_timetype = 'work'
                elif current_timetype == 'work':
                    next_timetype = 'break'
                self.speak_dialog('pomodoro.status', data={'duration': duration, 'timetype': next_timetype})
            else:
                self.speak("There isn't any pomodoro working right now to give status.")  # fallback

        def lg(self, string):
                LOGGER.debug('***')
                LOGGER.debug(string)

        def get_timeleft(self, inHuman=True):
            timetype = self.timetype  # the current working pomodoro, (work/break)
            timeleft = 0  # default timeleft for the next pomodoro

            if timetype == 'work':  # if current working timetype is 'work'
                timeleft = self.get_scheduled_event_status('work_time')  # get the status of the event 'work_time' which calles break_time()
            elif timetype == 'break':  # if current working timetype is 'break'
                timeleft = self.get_scheduled_event_status('break_time')  # get the status of the event 'break_time' which calles work_time()
            if inHuman:  # if the format is human readable (not in seconds)
                timeleft = get_time_human(timeleft)
                return timeleft
            else:  # if the format is in seconds
                return timeleft

        def process_pomodoro_inputs(self, message):
            """ Parse inputs
                Args:
                        message (Message): object passed by messagebus
            """
            wduration = message.data.get("workduration")
            bduration = message.data.get("breakduration")
            if not (wduration is None):  # work duration equals the user input if inputed
                self.work_duration = wduration
            if not (bduration is None):  # break duration equals the user input if inputed
                self.break_duration = bduration

        def work_time(self):
            if self.cycles == self.long_break_frequency:  # if reached one run
                self.cycles = 0  # reset cycles to restart fresh ones
                self.runs += 1  # add a run into the count
            if self.cycles == 0:  # speak the special pomodoro.start dialog in the first cycle
                if self.break_duration != "5 minutes":  # if user has inputed a break duration say the difference
                    self.speak_dialog(
                        'pomodoro.start.first.time.with.break',
                        data={'workduration': self.work_duration, 'breakduration': self.break_duration})
                elif self.break_duration == "5 minutes":  # if not then no need for saying the new val
                    self.speak_dialog(
                        'pomodoro.start.first.time',
                        data={'duration': self.work_duration})
                self.setuptime(self.break_time, self.work_duration, 'work_time')
            else:  # if it is not the first cycle
                self.speak_dialog('pomodoro.work.time', data={'duration': self.work_duration})
                self.setuptime(self.break_time, self.work_duration, 'work_time')  # setting up the  timer

            self.isworking = True

        def break_time(self):
            if self.cycles == self.long_break_frequency - 1:  # speak the long break dialog if it is the time to (according to the frequency var)
                self.speak_dialog('pomodoro.long.break.time', data={'duration': self.long_break_duration})  # speak long break dialog
                self.setuptime(self.work_time, self.long_break_duration, 'break_time')  # then start the timer with the long duration
            else:  # if it is not the time of the long break yet
                self.speak_dialog('pomodoro.break.time', data={'duration': self.break_duration})  # speak short break time dialog
                self.setuptime(self.work_time, self.break_duration, 'break_time')  # then start the timer with the short break duration
            self.cycles += 1  # just finished cycle, adding 1 to cycles count

        def cancel_timers(self):
            self.cancel_scheduled_event('work_time')  # cancel work_time event
            self.cancel_scheduled_event('break_time')  # cancel break_time event

        def setuptime(self, handle, duration, timer_name, cancel=True):
            if cancel:
                self.cancel_timers()  # reseting the prevoius events (timers)
            timer = parse_to_datetime(duration)  # parsing duration into datetime
            if timer_name == "break_time":
                self.record['breaknum'] += 1
                self.timetype = 'break'
            elif timer_name == "work_time":
                self.record['worknum'] += 1
                self.timetype = 'work'
            self.schedule_event(handle, timer, name=timer_name)  # scheduling the timer

        def handle_stop(self):
            if self.isworking:
                if self.get_response('pomodoro.stop') == 'yes':
                    self.give_report()
            self.stop()

        def stop(self):
            self.work_duration = "25 minutes"  # resetting the work duration to the default one
            self.break_duration = "5 minutes"  # resetting the break duration to the default one
            self.cancel_timers()  # stop all timers
            self.isworking = False  # setting it as not working
            self.record['worknum'] = 0  # resetting work number
            self.record['breaknum'] = 0  # resetting break number

        def give_report(self):
            """ Speaks the report of the last spent session
            """
            if self.isworking:  # checking if there's a pomodoro working or not
                timetype = self.timetype  # get the timetype of the current pomodoro (work/break)
                timeleft = self.get_timeleft(inHuman=False)  # get the time left for the next pomodoro (work/break) in secs
                worknum = self.record['worknum']  # number of works have been done (including the current one)
                breaknum = self.record['breaknum']  # number of break have been done (including the current one)
                workspent = 0  # for storing time spent in work runs
                breakspent = 0  # for storing time spent in break runs
                timespentnow = 0  # for current (work/break) pomodoro spent time so far (not finished yet)
                workduration = get_sec(parse_to_datetime(self.work_duration, timeleft=True))  # work duration set in secs
                breakduration = get_sec(parse_to_datetime(self.break_duration, timeleft=True))  # break duration set in secs
                long_breakduration = get_sec(parse_to_datetime(self.long_break_duration, timeleft=True))  # long_break duration in secs
                if timetype == 'break':  # if the *NEXT* timetype is work
                    breaknum -= 1  # then we know it's braek now, so we're taking 1 from the record so we calculate it separately
                    timespentnow += breakduration - timeleft  # time spent so far
                    breakspent += timespentnow
                elif timetype == 'work':  # if the *NEXT* timetype is break
                    worknum -= 1  # the same as above
                    timespentnow += workduration - timeleft  # time spent so far
                    workspent += timespentnow
                breaknum -= self.runs
                breakspent += breaknum * breakduration  # total time spent in finished short breaks (secs)
                breakspent += self.runs * long_breakduration
                breaknum += self.runs
                workspent += worknum * workduration  # total time spent in finished works
                workspent_ = get_time_human(workspent)
                breakspent_ = get_time_human(breakspent)
                totalspent = get_time_human(workspent + breakspent)
                if worknum == 1:
                    worknum_ = str(worknum)+" work"
                else:
                    worknum_ = str(worknum)+" works"
                if breaknum == 1:
                    breaknum_ = str(breaknum) + " break"
                else:
                    breaknum_ = str(breaknum) + " breaks"

                self.speak_dialog(
                    'report',
                    data={
                        'worknum': worknum_,
                        'breaknum': breaknum_,
                        'workspent': workspent_,
                        'breakspent': breakspent_,
                        'totalspent': totalspent,
                        'runnum': self.runs
                        })


def create_skill():
    return PomodoroSkill()
