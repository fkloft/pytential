from gi.repository import GLib
import dbus
import dbus.service
from dbus.mainloop.glib import DBusGMainLoop

STATES = [
	"Unknown",
	"Charging",
	"Discharging",
	"Empty",
	"Fully charged",
	"Pending charge",
	"Pending discharge",
]

DBusGMainLoop(set_as_default=True)

bus = dbus.SystemBus()
proxy = bus.get_object('org.freedesktop.UPower', '/org/freedesktop/UPower')
obj = dbus.Interface(proxy, 'org.freedesktop.UPower')

class Device:
	def __init__(self, path):
		self.path = path
		
		self.obj = bus.get_object('org.freedesktop.UPower', path)
		self.iface = dbus.Interface(self.obj, 'org.freedesktop.UPower.Device')
		self.props = dbus.Interface(self.obj, 'org.freedesktop.DBus.Properties')
	
	def get_properties(self):
		return self.props.GetAll("org.freedesktop.UPower.Device")
	
	def __getitem__(self, key):
		return self.props.Get("org.freedesktop.UPower.Device", key)
	
	def add_property_handler(self, cb):
		self.props.connect_to_signal("PropertiesChanged", cb)
	
	def is_battery(self):
		return self["Type"] == 2
	
	def get_state(self):
		return STATES[self["State"]]
	
	def get_percentage(self):
		return self["Percentage"]
	

def enumerate_devices():
	return [Device(path) for path in obj.EnumerateDevices()]

def get_battery():
	return [device for device in enumerate_devices() if device.is_battery()][0]

def loop():
	try: 
		GLib.MainLoop().run() 
	except KeyboardInterrupt: 
		GLib.MainLoop().quit() 

battery = get_battery()

def main():
	def on_property_change(interface, changed, removed):
		if "Percentage" in changed or "State" in changed:
			print(battery.get_state())
			print("%3d %%" % battery.get_percentage())
		
	
	battery.add_property_handler(on_property_change)
	
	loop()

if __name__ == "__main__":
	main()

