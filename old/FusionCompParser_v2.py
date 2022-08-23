from functools import reduce
import re
import pprint
import io
import ast

# Originally based on JSON parser from
# https://github.com/geekskool/python-json-parser/blob/master/jsonparse.py

lua_list_re = re.compile( r'^([a-zA-Z0-9"_\-.\[\]]+)(?:\s=\s{)(?:\s|\R)|^{\n' )
lua_obj_re = re.compile( r'^([a-zA-Z0-9_]+\s{)|^([a-zA-Z0-9_\-]+)\s=\s([a-zA-Z0-9_\-.\(\)]+\s{)|^(\[[a-zA-Z0-9".\]]+)\s=\s([a-zA-Z0-9_\-]+\s{)' )
lua_var_re = re.compile( r'^([a-zA-Z0-9_\[\]"]+)(?:\s=\s)([a-zA-Z0-9\s":\\\-\/_.&!@#$%^]+[,])' )
lua_list_var_re = re.compile( r'^{.+},')
lua_val_re = re.compile( r'(^\d+,)|(^["a-zA-Z0-9:\\\-\/_. ]+,)' )

class LuaObject():
	#__slots__ = ('name', 'value', 'varName')
	def __init__(self, className, value=[], varName=None):
		self.className = className
		self.value = value
		self.varName = varName

	def __str__(self):
		return (str(self.varName) + ' = ' + str(self.className) +  str(self.value) )

class LuaVariable():
	#__slots__ = ('varName', 'value', 'className')
	def __init__(self, varName, value):
		self.varName = varName
		self.value = value[:-1] #remove comma
		self.className  = self.getClassName()

	def is_float(self, value):
		try:
			float(value)
			return True
		except:
			return False

	def getClassName(self):
		if re.match(r'"', self.value):
			self.value = ast.literal_eval(self.value)
			return "string"
		elif self.value.lower() in ['true', 'false']:
			return "bool"
		elif self.is_float(self.value):
			return "float"
		else:
			return "None"

	def __str__(self):
		return (str(self.varName) + ' = ' + str(self.value))


def lua_obj_parser(data):
	# SomeVarName = Object {
	# Object {
	# ["Some.Name.Variable"] = Somename {
	res = lua_obj_re.match(data.strip())
	
	if not res:
		return None
	lua_obj = None
	
	if res.group(1):
		# Object with no variable name assigned
		lua_obj = LuaObject (res.group(1)[:-2], [], None)
	elif res.group(2) and res.group(3):
		# Object with a variable name
		lua_obj = LuaObject (res.group(3)[:-2], [], res.group(2))
	elif res.group(4) and res.group(5):
		# Object with List as variable name 
		lua_obj = LuaObject (res.group(4)[:-2], [], res.group(5))

	#pos = data.find('{')
	#if pos != (res.end()-1):
	#	print('pos: ', pos, 'res.end.group(1): ',  (res.end()-1) )
	#data = data[pos + 1:].strip()
	data = data[res.end():].strip()

	while data[0] != '}':
		res = lua_obj_parser(data)
		if res:
			lua_obj.value.append(res[0])
			data = res[1]
		
		res = lua_list_parser(data)
		if res:
			lua_obj.value.append(res[0])
			data = res[1]
		
		res = lua_var_parser(data)
		if res:
			lua_obj.value.append(res[0])
			data = res[1]

		res = lua_list_var_parser(data)
		if res:
			lua_obj.value.append(res[0])
			data = res[1]
		
		res = lua_val_parser(data)
		if res:
			lua_obj.value.append(res[0])
			data = res[1]
		
		if data.strip()[0] == "}":
			return [lua_obj, data[2:].strip()]

	return [lua_obj, data[2:].strip()]

def lua_val_parser(data):
	# Matches simple values
	# "Something",
	# 123,
	res = lua_val_re.match(data)
	
	if res:
		#pos = data.find(',')
		if res.group(1):
		# return value , rest of the string
			#print('pos: ', pos, 'res.end.group(1): ',  (res.end()-1) )
			#return [res.group(1)[:-1], data[pos + 1:].strip()] #remove trailing comma
			return [res.group(1)[:-1], data[res.end():].strip()] #remove trailing comma
		elif res.group(2) != None:
			#print('pos: ', pos, 'res.end.group(2): ',  (res.end()-1) )
			s = res.group(2)[:-1]
			return [ast.literal_eval(s), data[res.end():].strip()] #remove trailing comma
	else:
		return None

def lua_list_var_parser(data):
	res = lua_list_var_re.match(data)

	if not res:
		return None

	lua_list = LuaObject("ListObject", [res.group(0)], None)
	pos = data.find('}')
	#if pos+2 != (res.end()):
	#	print('N pos: ', pos+2, 'res.end.group(1): ',  (res.end()) )
	#else:
	#	print('Y pos: ', pos+2, 'res.end.group(1): ',  (res.end()) )

	return [lua_list, data[pos + 2:].strip()]

def lua_list_parser(data):
	# SomeVarName = {
	# SomeVarName = { },
	# { #empty start of list
	res = lua_list_re.match(data.strip())
	
	#if not res or ( '{' not in data[0:(data.find('\n'))]): #workaround bad regex
	if not res:
		return None
	
	lua_list = None
	
	if res.group(1):
		#if '{' not in data[0:(data.find('\n'))]:
		#	print('ERROR')
		lua_list = LuaObject("ListObject", [], res.group(1))
	elif res.group(0):
		lua_list = LuaObject("ListObject", [], None)
	
	#pos = data.find('{')
	#if pos != (res.end()-2):
	#	print('N pos: ', pos, 'res.end.group(1): ',  (res.end()-2) )
	#else:
	#	print('Y pos: ', pos, 'res.end.group(1): ',  (res.end()-2) )
	data = data[(res.end()-1):].strip()

	while data[0:2] != "},":
		res = lua_obj_parser(data)
		if res:
			lua_list.value.append(res[0])
			data = res[1]
		#print(len(data))
		res = lua_list_parser(data)
		if res:
			lua_list.value.append(res[0])
			data = res[1]
		#print(len(data))
		res = lua_var_parser(data)
		if res:
			lua_list.value.append(res[0])
			data = res[1]
		#print(len(data))
		res = lua_list_var_parser(data)
		if res:
			lua_list.value.append(res[0])
			data = res[1]
		#print(len(data))
		res = lua_val_parser(data)
		if res:
			lua_list.value.append(res[0])
			data = res[1]
		#print(len(data))
		if data.strip()[0:2] == "},":
			return [lua_list, data[2:].strip()]
	
	return [lua_list, data[2:].strip()]

def lua_var_parser(data):
	# SomeVarName = "something",
	# SomeVarName = 123,
	res = lua_var_re.match(data)
	
	if res:
		#pos = data.find(',')
		#print('pos: ', pos, 'res.end.group(1): ',  (res.end()-1) )
		#return [LuaVariable(res.group(1), res.group(2)), data[pos + 1:].strip()]
		return [LuaVariable(res.group(1), res.group(2)), data[res.end():].strip()]
	else:
		return None

def get_by_varName(compTree, varName):
	result = None
	for obj in compTree.value:
		#print(obj)
		#print(obj.__class__.__name__)
		if obj.__class__.__name__ == "LuaObject" or obj.__class__.__name__ == "LuaVariable":
			if obj.varName == varName:
				return obj
			elif obj.__class__.__name__ == "LuaObject":
				result =   get_by_varName(obj, varName)
				if result:
					return result
	return result

def get_by_className(compTree, className):
	result = None
	for obj in compTree.value:
		#print(obj)
		#print(obj.__class__.__name__)
		if obj.__class__.__name__ == "LuaObject" or obj.__class__.__name__ == "LuaVariable":
			if obj.className == className:
				return obj
			elif obj.__class__.__name__ == "LuaObject":
				result = get_by_className(obj, className)
				if result:
					return result
	return result

def get_all_by_className(compTree, className):
	result = []
	for obj in compTree.value:
		#print(obj)
		#print(obj.__class__.__name__)
		if obj.__class__.__name__ == "LuaObject" or obj.__class__.__name__ == "LuaVariable":
			if obj.className == className:
				result.append(obj)
			elif obj.__class__.__name__ == "LuaObject":
				objList = get_all_by_className(obj, className)
				if len(objList):
					result = result + objList
	return result

def get_all_by_varName(compTree, varName):
	result = []
	for obj in compTree.value:
		#print(obj)
		#print(obj.__class__.__name__)
		if obj.__class__.__name__ == "LuaObject" or obj.__class__.__name__ == "LuaVariable":
			if obj.varName == varName:
				result.append(obj)
			elif obj.__class__.__name__ == "LuaObject":
				objList = get_all_by_varName(obj, varName)
				if len(objList):
					result = result + objList
	return result


def all_parsers(*args):
	return lambda data: (reduce(lambda f, g: f if f(data) else g, args)(data))


def parse_comp_file(file_name):
	lua_value_parser = all_parsers(lua_obj_parser)

	with open(file_name, "r") as f:
		data = f.read()
	print(len(data))
	res = lua_value_parser(data.strip())
	
	try:
		comp = res[0]
		return comp
	except TypeError:
		return None

def main():
	file_name = "test.comp"
	comp = parse_comp_file(file_name)
	if comp:
		Loaders = get_all_by_varName(comp, "Clips")
		for o in Loaders:
			print(o)
	else:
		print("Error parsing comp file.")

if __name__ == "__main__":
	main()

'''
From xml parser
while True:
	data = source.read(65536)
	if not data:
		break
	parser.feed(data)
self._root = parser.close()
return self._root

'''