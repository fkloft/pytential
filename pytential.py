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
	
	def is_registered(self):
		if not self.devices:
			self.get_devices()
		
		if not "device_id" in self.config:
			return False
		
		return len([True for dev in self.devices if dev["device_id"] == self.config["device_id"]]) > 0
	
	def register(self):
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
	
	def get_object_id(self):
		if "objectId" in self.config:
			return self.config["objectId"]
		
		if not "device_id" in self.config:
			return None
		
		devices = [dev for dev in self.get_devices() if dev["device_id"] == self.config["device_id"]]
		if len(devices) == 0:
			return None
		
		dev = devices[0]
		self.config["objectId"] = dev["objectId"]
		self.save_config()
		return dev["objectId"]
	
	def update(self):
		data = {
			"objectId": self.get_object_id(),
		}
		data.update(sysinfo.get_power_state())
		
		r = self.post('functions/updateBattery', json=data)
		assert r.json()["result"]
		
		data["low_battery_push_sent"] = False
		r = self.put('classes/Device/%s' % self.get_object_id(), json=data)
		return r.json()
	
	def post(self, url, *args, **kwargs):
		return post(url, headers={
			"X-Parse-Session-Token": self.config["user"]["sessionToken"],
		}, *args, **kwargs)
	
	def put(self, url, *args, **kwargs):
		return put(url, headers={
			"X-Parse-Session-Token": self.config["user"]["sessionToken"],
		}, *args, **kwargs)
	

