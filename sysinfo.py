import subprocess
import upower

def get_rf_state(identifier):
	data = subprocess.check_output(("rfkill", "list", identifier)).decode()
	
	if " blocked: yes\n" in data:
		return False
	return True

def get_power_state():
	#capacity = int(open("/sys/class/power_supply/BAT0/capacity").read().strip())
	#state = open("/sys/class/power_supply/BAT0/status").read().strip()
	capacity = upower.battery.get_percentage()
	state = upower.battery.get_state()
	
	wifi = get_rf_state("wifi")
	bluetooth = get_rf_state("bluetooth")
	
	return {
		"bluetooth_state": bluetooth,
		"state": state,
		"value": capacity,
		"wifi_state": wifi,
	}

def get_vendor():
	return open("/sys/devices/virtual/dmi/id/sys_vendor").read().strip()

def get_product():
	return open("/sys/devices/virtual/dmi/id/product_name").read().strip()

