from adapt.intent import IntentBuilder
from mycroft.skills.core import MycroftSkill
from mycroft.util.log import getLogger

__author__ = 'erabti'

LOGGER = getLogger(__name__)

class PomodoroSkill(MycroftSkill):
	def __init__(self):
		super(PomodoroSkill, self).__init__(name="PomodoroSkill")
		
	def initialize(self):
        set_intent = IntentBuilder("SetIntent").require("SetPomodoroSkill").build()
        self.register_intent(set_intent, self.set_intent)
	def set_intent (self, message):
		self.speak_dialog("pomodoro.set")
		
	def stop(self):
	pass
