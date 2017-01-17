#!/usr/bin/env python3

import argparse
import getpass
import json

import pytential
import upower

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
					"manufacturer_name": "<none>",
					"model_number": "<none>",
				}
				d.update(device)
				
				print("""
  Name:      %(name)s
  Vendor:    %(manufacturer_name)s
  Model:     %(model_number)s
  Type:      %(device_type)s
  Device ID: %(device_id)s
  Object ID: %(objectId)s
  Updated:   %(updatedAt)s
  Battery:   %(value)d%%
  State:     %(state)s
  Wi-Fi:     %(wifi_state)s
  Bluetooth: %(bluetooth_state)s""" % d)
	
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

