from ctypes import *
import collections

libCSM = CDLL("../build/libcommotion-service-manager.so")

libCSM.services_fetch.argtypes = [POINTER(c_void_p)]
libCSM.services_free.argtypes = [c_void_p]

libCSM.service_create.restype = c_void_p
libCSM.service_commit.argtypes = [c_void_p]
libCSM.service_remove.argtypes = [c_void_p]

libCSM.services_get_by_index.argtypes = [c_void_p, c_int]
libCSM.services_get_by_index.restype = c_void_p
libCSM.services_get_by_key.argtypes = [c_void_p, c_char_p]
libCSM.services_get_by_key.restype = c_void_p

libCSM.service_is_local.argtypes = [c_void_p]

libCSM.service_fields_get_length.argtypes = [c_void_p]
libCSM.service_field_get_next.argtypes = [c_void_p, c_void_p, POINTER(c_char_p)]
libCSM.service_field_get_next.restype = c_void_p
libCSM.service_field_get_by_name.argtypes = [c_void_p, c_char_p]
libCSM.service_field_get_by_name.restype = c_void_p

libCSM.service_field_get_name.argtypes = [c_void_p]
libCSM.service_field_get_name.restype = c_char_p
libCSM.service_field_get_type.argtypes = [c_void_p]
libCSM.service_field_get_int.argtypes = [c_void_p]
libCSM.service_field_get_int.restype = c_long
libCSM.service_field_get_string.argtypes = [c_void_p]
libCSM.service_field_get_string.restype = c_char_p

libCSM.service_field_get_list_subtype.argtypes = [c_void_p]
libCSM.service_field_get_list_length.argtypes = [c_void_p]
libCSM.service_field_get_list_int.argtypes = [c_void_p, c_int]
libCSM.service_field_get_list_int.restype = c_long
libCSM.service_field_get_list_string.argtypes = [c_void_p, c_int]
libCSM.service_field_get_list_string.restype = c_char_p

libCSM.service_set_int.argtypes = [c_void_p, c_char_p, c_long]
libCSM.service_set_string.argtypes = [c_void_p, c_char_p, c_char_p]
libCSM.service_set_int_list_from_array.argtypes = [c_void_p, c_char_p, POINTER(c_long), c_int]
libCSM.service_set_string_list_from_array.argtypes = [c_void_p, c_char_p, POINTER(c_char_p), c_int]

#typedef enum {
  #CSM_FIELD_STRING = 1,
  #CSM_FIELD_LIST,
  #CSM_FIELD_INT,  /** int32_t */
  #CSM_FIELD_HEX,
#} csm_field_type;

class FieldType:
    STRING,LIST,INT,HEX = range(1,5)

# TODO set these as restype for libCSM functions
def CheckSimpleError(ret):
    if ret == -1:
	raise RuntimeError
    return ret

def CheckPointerError(ret):
    if not ret.value: # function returned NULL
	raise RuntimeError
    return ret

class CSMSchema(object):
    def __init__(self):
	self.fields = []
	schema = c_void_p
	#self.len = libCSM.schema_fetch(byref(schema))
	
    def get_type(self, name):
      pass
    
    def get_subtype(self, name):
      pass
    
    def get_required(self, name):
      pass

class CSMSchemaField(object):
    def __init__(self,name,field_type,required=False):
	self.name = name
	if (field_type != 'INT' and field_type != 'STR' and field_type != 'LIST'):
	    raise TypeError
	self.field_type = field_type
	self.required = required

class CSMSchemaFieldInt(CSMSchemaField):
    def __init__(self,name,val,required=False):
	CSMSchemaField.__init__(self,name,'INT',required)
	self.val = val
	self.min = None
	self.max = None

class CSMSchemaFieldString(CSMSchemaField):
    def __init__(self,name,val,required=False):
	CSMSchemaField.__init__(self,name,'STR',required)
	self.val = val
	self.length = None
	
class CSMSchemaFieldList(CSMSchemaField):
    def __init__(self,name,subtype,required=False):
	if (subtype != 'INT' and subtype != 'STR'):
	    raise TypeError
	CSMSchemaField.__init__(self,name,'LIST',required)
	self.subtype = subtype

csm_schema = CSMSchema()

class CSMServiceList(collections.Mapping):
    def __init__(self):
	self.__services = None
	self.__len = 0
	self.update()
    
    def __len__(self):
	return self.__len
    
    def __getitem__(self,key):
	if not key:
	    raise KeyError
	if not isinstance(key, basestring):
	    raise TypeError
	return CSMService(libCSM.services_get_by_key(self.__services,key))
	
    def __iter__(self):
	for i in range(self.__len):
	    yield CSMService(libCSM.services_get_by_index(self.__services,i))
    
    def __delitem__(self,key):
	assert libCSM.service_remove(libCSM.services_get_by_key(self.__services,key)).value == 1
	self.update()
    
    def append(self,value):
	if not isinstance(value,CSMService):
	    raise TypeError
	assert libCSM.service_commit(value.ptr).value == 1
	self.update()
    
    def update(self):
        """ Free's current list of services and repopulates it from the Commotion service manager."""
	# first, free current list of services
	if (self.__services and self.__len):
	    assert libCSM.services_free(self.__services).value == 1
	
	# next, fetch list of services from CSM
	self.__services = c_void_p
	self.__len = libCSM.services_fetch(byref(self.__services)).value
	
class CSMService(object):
    """A service object that handles service creation, modification, comparison, and deletion."""
    def __init__(self, schema, ptr=None):
        """
        Uses a pointer to load an existing service, or requests a pointer for a new Commotion service.
        
        ptr : C pointer to a commotion service
        """
        self.__dirty = False
        self.__local = 1
        if not isinstance(schema, CSMSchema):
	    raise TypeError
	self.__schema = schema
        if ptr:
            if type(ptr) != c_void_p:
		raise TypeError
            self.ptr = ptr
            # fetch all fields so client can display service
            self.__len = libCSM.service_fields_get_length(field)
            key = c_char_p
            field = libCSM.service_field_get_next(self.ptr, None, byref(key))
            while field.value:
		field_type = libCSM.service_field_get_type(field)
		if field_type == FieldType.STRING or field_type == FieldType.HEX:
		    self.__dict__[key] = libCSM.service_field_get_string(field).value
		elif field_type == FieldType.INT:
		    self.__dict__[key] = libCSM.service_field_get_int(field)
		elif field_type == FieldType.LIST:
		    field_subtype = libCSM.service_field_get_list_subtype(field)
		    list_len = libCSM.service_field_list_get_length(field)
		    self.__dict__[key] = []
		    if field_subtype == FieldType.INT:
			for i in range(list_len):
			    self.__dict__[key].append(libCSM.service_field_get_list_int(field,i))
		    elif field_subtype == FieldType.STRING or field_subtype == FieldType.HEX:
			for s in range(list_len):
			    self.__dict__[key].append(libCSM.service_field_get_list_string(field,i).value)
		    else:
			raise TypeError
		else:
		    raise TypeError
		# get next field
		field = libCSM.service_field_get_next(self.ptr, field, byref(key))
            # flag to indicate whether service is local/editable or not
            if libCSM.service_is_local(self.ptr) == 0:
		self.__local = 0
        else:
            self.ptr = libCSM.service_create()
            self.__len = 0
    
    def is_current(self):
	return not self.__dirty
    
    def __len__(self):
	return self.__len
    
    def __setattr__(self,name,value):
	if not self.__local:
	    raise TypeError
	field = libCSM.service_field_get_by_name(self.ptr, name)
	if field.value:
	    field_type = libCSM.service_field_get_type(field).value
	if isinstance(value,int) or isinstance(value,long):
	    if field_type and field_type != FieldType.INT:
		raise TypeError
	    assert libCSM.service_set_int(self.ptr, name, c_long(value)).value == 1
	elif isinstance(value, basestring):
	    if field_type and field_type != FieldType.STRING and field_type != FieldType.HEX:
		raise TypeError
	    assert libCSM.service_set_string(self.ptr, name, value).value == 1
	elif isinstance(value, list):
	    if field_type:
		if field_type != FieldType.LIST:
		    raise TypeError
		field_subtype = libCSM.service_field_get_list_subtype(self.ptr).value
	    list_len = len(value)
	    if list_len <= 0:
		raise ValueError
	    subtype = type(value[0])
	    for x in value:
		if type(x) != subtype:
		    raise TypeError
	    if subtype == int or subtype == long:
		if field_subtype and field_subtype != FieldType.INT:
		    raise TypeError
		new_list = (c_long * list_len)(*value)
		assert libCSM.service_set_int_list_from_array(self.ptr,name,new_list,list_len).value == 1
	    elif subtype == str:
		if field_subtype and field_subtype != FieldType.STRING and field_subtype != FieldType.HEX:
		    raise TypeError
		new_list = (c_char_p * list_len)(*value)
		assert libCSM.service_set_string_list_from_array(self.ptr,name,new_list,list_len).value == 1
	    else:
		raise TypeError
	else:
	    raise TypeError
	self.__dirty = True
    
    # TODO can we assume schema will match with service?
    def __getattr__(self,name):
	field = libCSM.service_field_get_by_name(self.ptr, name)
	if not field.value:
	    raise LookupError
	field_type = libCSM.service_field_get_type(field).value
	if field_type == FieldType.INT:
	    return libCSM.service_field_get_int(field).value
	elif field_type == FieldType.STRING or field_type == FieldType.HEX:
	    return libCSM.service_field_get_str(field)
	
	
	
	field_type = self.__schema.get_type(name)
	if field_type == 'INT':
	    return libCSM.service_get_int(self.ptr,name).value
	elif field_type == 'STR':
	    return libCSM.service_get_str(self.ptr,name).value
	elif field_type == 'LIST':
	    subtype = self.__schema.get_subtype(name)
	    ret = []
	    list_p = c_void_p
	    list_len = libCSM.service_get_list(self.ptr,name,byref(list_p)).value
	    if subtype == 'INT':
		for i in range(list_len):
		    ret.append(libCSM.service_list_get_int(list_p,c_int(i)).value)
	    elif subtype == 'STR':
		for s in range(list_len):
		    ret.append(libCSM.service_list_get_str(list_p,c_int(i)).value)
	    else:
		raise TypeError
	else:
	    raise TypeError
    
    def __delattr__(self,name):
	if not self.__local:
	    raise TypeError
	assert libCSM.service_remove_field(self.ptr,name).value == 1
	self.__dirty = True
    
    def __eq__(self, other):
        """Test equality of this service and another.

        other : CSMService object
        return : bool
        """
        return (isinstance(other, self.__class__)
            and self.__dict__ == other.__dict__)
        #return (isinstance(other, self.__class__)
            #and self.ptr == other.ptr)

    def __ne__(self, other):
        """Test inequality of this service and another.

        other : CSMService object
        return : bool
        """
        return not self.__eq__(other)
    
    def __repr__(self):
        """
        The official string representation of this service, formatted as a valid Python expression to recreate it.

        return : string
        """
	pass
    
    def __str__(self):
	"""
        The human readable string representation of this service.

        return : string
        """
	pass
    
    def commit_service(self):
        """Sets current service values to its pointer in the Commotion Service Manager """
        if not self.__local:
	    raise TypeError
        if not self.__dirty:
	    return
	# Upon commiting, key and signature will be set
	assert libCSM.commit_service(self.ptr).value == 1
	self.__dirty = False
    
    def remove_service(self):
        """Removes the service in both the Commotion Service Manager and locally."""
        if not self.__local:
	    raise TypeError
        assert libCSM.remove_service(self.ptr).value == 1
        self.__del__(self)



		#key = c_char_p
		#val = c_void_p
		#field_type = libCSM.service_get_field(byref(key), byref(val)).value
		#if field_type == FieldType.STRING or field_type == FieldType.HEX:
		    #self.__dict__[key.value] = cast(val, c_char_p).value
		#elif field_type == FieldType.INT:
		    #self.__dict__[key.value] = cast(val, POINTER(c_long)).contents.value
		#elif field_type == FieldType.LIST:
		    #field_subtype = libCSM.service_get_list_subtype(field)