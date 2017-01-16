#!/usr/bin/env python3

import argparse
import getpass

import pytential
import upower

def main():
	parser = argparse.ArgumentParser()
	
	parser.add_argument("-u", "--update",  action="store_true", help="update battery level")
	parser.add_argument("-l", "--list",    action="store_true", help="list devices")
	parser.add_argument("-d", "--daemon",  action="store_true", help="run daemon")
	
	parser.add_argument("-v", "--verbose", action="store_true", help="verbose mode")
	
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
				print("updated:", result)
		else:
			result = p.register()
			if args.verbose:
				print("registered:", result)
	
	if args.list:
		devices = p.get_devices()
		
		if args.verbose:
			print("devices:", devices)
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
  Battery:   %(value)d%%
  State:     %(state)s
  Updated:   %(updatedAt)s
  Wi-Fi:     %(wifi_state)s
  Bluetooth: %(bluetooth_state)s""" % d)
	
	if args.daemon:
		def on_property_change(interface, changed, removed):
			if "Percentage" in changed or "State" in changed:
				if args.verbose:
					print("changed:", upower.battery.get_percentage(), upower.battery.get_state())
				result = p.update()
				if args.verbose:
					print("updated:", result)
		
		upower.battery.add_property_handler(on_property_change)
		upower.loop()
	

if __name__ == "__main__":
	main()

