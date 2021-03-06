#!/usr/bin/env python3

import argparse
import getpass
import json
import dateutil.parser
import ago

import pytential
import upower

def format_time(timestring):
	timestamp = dateutil.parser.parse(timestring)
	timestamp = timestamp.astimezone() # to local timezone
	
	return "%s - %s" % (timestamp.strftime("%Y-%m-%d %H:%M:%S"), ago.human(timestamp, abbreviate=True, precision=1))

def main():
	parser = argparse.ArgumentParser()
	
	parser.add_argument("-u", "--update",  action="store_true", help="update battery level")
	parser.add_argument("-l", "--list",    action="store_true", help="list devices")
	parser.add_argument("-d", "--daemon",  action="store_true", help="run daemon")
	
	group = parser.add_argument_group(description="Use these options to remotely enable/disable bluetooth or wifi or to ring a device."
		+ " Pass either the device_id or objectId (see -l) or the device label, if it is unique."
		+ " These options can be specified multiple times.")
	group.add_argument("-r", "--ring",              action="append", metavar="DEV", help="ring device")
	group.add_argument("-b", "--disable-bluetooth", action="append", metavar="DEV", help="disable bluetooth")
	group.add_argument("-B", "--enable-bluetooth",  action="append", metavar="DEV", help="enable bluetooth")
	group.add_argument("-w", "--disable-wifi",      action="append", metavar="DEV", help="disable wifi")
	group.add_argument("-W", "--enable-wifi",       action="append", metavar="DEV", help="enable wifi")
	
	parser.add_argument("-v", "--verbose", action="store_true", help="verbose, machine-readable mode. each output line can be parsed as JSON")
	
	args = parser.parse_args()
	
	try:
		p = pytential.Pytential()
	except pytential.LoginError:
		if args.daemon:
			raise
		
		username = input("E-Mail: ")
		password = getpass.getpass()
		pytential.login(username, password)
		
		p = pytential.Pytential()
	
	if args.update:
		if p.is_registered():
			result = p.update()
			if args.verbose:
				print(json.dumps({"status": "updated", "result": result, }))
		else:
			result = p.register()
			if args.verbose:
				print(json.dumps({"status": "registered", "result": result, }))
	
	if args.list:
		devices = p.get_devices()
		
		if args.verbose:
			print(json.dumps({"status": "devices", "result": devices, }))
		else:
			print("Devices:")
			for device in p.get_devices():
				d = {
					"manufacturer_name": "\033[33m<none>\033[0m",
					"model_number": "\033[33m<none>\033[0m",
				}
				d.update(device)
				d["updatedAtF"] = format_time(d["updatedAt"])
				
				d["wifi_f"]      = d["wifi_state"]      and "\033[2;32m⌔ Enabled" or u"\033[2;31m\u0338⌔ Disabled"
				d["bluetooth_f"] = d["bluetooth_state"] and "\033[34mꔪ Enabled" or u"\033[33m\u0338ꔪ Disabled"
				
				d["state_c"] = "\033[2;33m"
				if d["state"].lower() in ("charging", "fully charged", "pending charge"):
					d["state_c"] = "\033[2;32m"
				elif d["state"].lower() in ("discharging", "empty", "pending discharge"):
					d["state_c"] = "\033[2;31m"
				
				level_colors = ("2;31", "0;31", "0;33", "2;32", "0;32")
				d["level_c"] = level_colors[round(d["value"] / 100.0 * (len(level_colors) - 1))]
				
				print("""
  Name:      %(name)-20s\
  Vendor:    %(manufacturer_name)s
  Type:      %(device_type)-20s\
  Model:     %(model_number)s
  Device ID: %(device_id)-20s\
  Object ID: %(objectId)s
  Battery:   \033[%(level_c)sm%(value)3d%%\033[0m                \
  Wi-Fi:     %(wifi_f)s\033[0m
  State:     %(state_c)s%(state)-20s\033[0m\
  Bluetooth: %(bluetooth_f)s\033[0m
  Updated:   %(updatedAtF)s
  """.rstrip() % d)
	
	if args.ring:
		for dev in args.ring:
			result = p.ring_device(dev)
			if args.verbose:
				print(json.dumps({"status": "remote_control", "device": dev, "feature": "ring", "result": result, }))
			elif result:
				print("Ringed device %s" % dev)
			else:
				print("Failed to ring on %s" % dev)
	
	if args.enable_bluetooth:
		for dev in args.enable_bluetooth:
			result = p.remote_control(dev, "BT", True)
			if args.verbose:
				print(json.dumps({"status": "remote_control", "device": dev, "feature": "bt", "enable": True, "result": result, }))
			elif result:
				print("Bluetooth enabled on %s" % dev)
			else:
				print("Failed to enable bluetooth on %s" % dev)
	
	if args.disable_bluetooth:
		for dev in args.disable_bluetooth:
			result = p.remote_control(dev, "BT", False)
			if args.verbose:
				print(json.dumps({"status": "remote_control", "device": dev, "feature": "bt", "enable": False, "result": result, }))
			elif result:
				print("Bluetooth disabled on %s" % dev)
			else:
				print("Failed to disable bluetooth on %s" % dev)
	
	if args.enable_wifi:
		for dev in args.enable_wifi:
			result = p.remote_control(dev, "wifi", True)
			if args.verbose:
				print(json.dumps({"status": "remote_control", "device": dev, "feature": "wifi", "enable": True, "result": result, }))
			elif result:
				print("Wifi enabled on %s" % dev)
			else:
				print("Failed to enable Wifi on %s" % dev)
	
	if args.disable_wifi:
		for dev in args.disable_wifi:
			result = p.remote_control(dev, "WIFI", False)
			if args.verbose:
				print(json.dumps({"status": "remote_control", "device": dev, "feature": "wifi", "enable": False, "result": result, }))
			elif result:
				print("WiFi disabled on %s" % dev)
			else:
				print("Failed to disable WiFi on %s" % dev)
	
	if args.daemon:
		def on_property_change(interface, changed, removed):
			if "Percentage" in changed or "State" in changed:
				if args.verbose:
					print(json.dumps({
						"status": "changed",
						"percentage": upower.battery.get_percentage(),
						"state": upower.battery.get_state(),
					}))
				result = p.update()
				if args.verbose:
					print(json.dumps({"status": "updated", "result": result, }))
		
		upower.battery.add_property_handler(on_property_change)
		upower.loop()
	

if __name__ == "__main__":
	main()

