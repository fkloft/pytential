import json
import os
import requests
import binascii

import sysinfo

BASE = "https://api.parse.com/1/"
HEADERS = {
	"X-Parse-Application-Id": "5E2cwyE1QNgn7deCOxAEzqcgm7qOR5s2aPCovrnw",
	"X-Parse-Client-Key": "NUcPzEslh494ssg1M3zmUzLw3A5vndcbAEeLOb5q",
}
CONFIG = os.path.expanduser("~/.pytential")

class LoginError(Exception):
	pass

def post(url, headers={}, *args, **kwargs):
	headers.update(HEADERS)
	return requests.post(BASE + url, headers=headers, *args, **kwargs)

def put(url, headers={}, *args, **kwargs):
	headers.update(HEADERS)
	return requests.put(BASE + url, headers=headers, *args, **kwargs)

def checkEmail(username):
	r = post('functions/checkIfEmailRegistered', json={
		"username": username,
	})
	
	return r.json()["result"]

def login(username, password):
	if not checkEmail(username):
		raise LoginError("E-Mail is not registered!")
	
	r = post('login', json={
		"_method": "GET",
		"username": username,
		"password": password,
	})
	
	data = r.json()
	json.dump({
		"user": data,
	}, open(CONFIG, "w"))
	return data

class Pytential:
	def __init__(self):
		try:
			self.config = json.load(open(CONFIG))
		except FileNotFoundError as e:
			raise LoginError(e)
		
		self.devices = None
	
	def save_config(self):
		json.dump(self.config, open(CONFIG, "w"))
	
	def get_devices(self):
		r = self.post('classes/Device', json={
			"_method": "GET",
			"where": json.dumps({
				"parent_user": {
					 "__type": "Pointer",
					 "className": "_User",
					 "objectId": self.config["user"]["objectId"],
				 },
			}),
		})
		
		self.devices = r.json()["results"]
		return self.devices
	
	def get_device(self, identifier=None):
		"Find device by either passing the objectId or the device_id. For identifier=None (default), return the local device. You can also pass the device's name, if it is unique (case-insensitive)."
		
		devices = self.get_devices()
		
		if identifier is None:
			for dev in devices:
				if ("objectId"  in self.config and dev["objectId" ] == self.config["objectId" ])\
				or ("device_id" in self.config and dev["device_id"] == self.config["device_id"]):
					self.config["objectId" ] = dev["objectId" ]
					self.config["device_id"] = dev["device_id"]
					self.save_config()
					return dev
		else:
			for dev in devices:
				if dev["device_id"] == identifier or dev["objectId"] == identifier:
					return dev
			
			matches = [dev for dev in devices if dev["name"].lower() == identifier.lower()]
			if len(matches) == 1: # and no more
				return matches[0]
			
		
		return None
	
	def assert_local_device(self):
		"assert that the local device_id and objectId are known"
		
		if "objectId"  in self.config and "device_id" in self.config:
			return
		self.get_device()
	
	def is_registered(self):
		return self.get_device() is not None
	
	def register(self):
		if self.is_registered():
			return None
		
		if not "device_id" in self.config:
			self.config["device_id"] = binascii.hexlify(os.urandom(8)).decode()
			self.save_config()
		
		vendor = sysinfo.get_vendor()
		product = sysinfo.get_product()
		
		data = {
			"ACL": {
				self.config["user"]["objectId"]: {
					"read": True,
					"write": True
				}
			},
			"device_id": self.config["device_id"],
			"device_type": "android_tab",
			"low_battery_threshold": 20,
			"manufacturer_name": vendor,
			"model_number": product,
			"name": "%s %s" % (vendor, product),
			"parent_user": {
				"__type": "Pointer",
				"className": "_User",
				"objectId": self.config["user"]["objectId"],
			},
		}
		
		data.update(sysinfo.get_power_state())
		
		r = self.post('classes/Device', json=data)
		response = r.json()
		if "objectId" in response:
			self.config["objectId"] = response["objectId"]
			self.save_config()
		return response
	
	def update(self):
		self.assert_local_device()
		
		data = {
			"objectId": self.config["objectId"],
		}
		data.update(sysinfo.get_power_state())
		
		r = self.post('functions/updateBattery', json=data)
		assert r.json()["result"]
		
		data["low_battery_push_sent"] = False
		r = self.put('classes/Device/%s' % self.config["objectId"], json=data)
		return r.json()
	
	def remote_control(self, device_id, feature, enable):
		features = {
			"BT": "Bluetooth",
			"WIFI": "WiFi",
		}
		feature = feature.upper()
		if feature not in features:
			raise ValueError("Unknown feature: %s" % feature)
		
		device = self.get_device(device_id)
		if not device:
			raise ValueError("Unknown device: %s" % device_id)
		
		if enable:
			action = "ON"
			label = "enabled"
		else:
			action = "OFF"
			label = "disabled"
		
		r = self.post('push', json={
			"data": {
				"action": "com.paranoidgems.potential.%s_%s" % (feature, action),
				"alert": "Your %s has been %s." % (features[feature], label),
				"title": "%s %s" % (features[feature], label),
			},
			"expiration_interval": 300,
			"where": {
				"device_id": device["device_id"],
				"username": self.config["user"]["username"],
			}
		})
		return r.json()["result"]
	
	def post(self, url, *args, **kwargs):
		return post(url, headers={
			"X-Parse-Session-Token": self.config["user"]["sessionToken"],
		}, *args, **kwargs)
	
	def put(self, url, *args, **kwargs):
		return put(url, headers={
			"X-Parse-Session-Token": self.config["user"]["sessionToken"],
		}, *args, **kwargs)
	

