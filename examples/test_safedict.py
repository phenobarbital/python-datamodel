from datamodel.typedefs.types import SafeDict, AttrDict, NullDefault

# Example usage of SafeDict
conditions = {"name": "John", "age": 30}
cql = "SELECT * FROM users WHERE name = {name} AND city = {city}"
safe_cql = cql.format_map(SafeDict(**conditions))
print(safe_cql)  # Output: SELECT * FROM users WHERE name = John AND city = {city}

# Example usage of AttrDict
data = AttrDict({"a": 1, "b": 2})
print(data.a)  # Output: 1
data.c = 3
print(data)    # Output: {'a': 1, 'b': 2, 'c': 3}

# Example usage of NullDefault
my_dict = NullDefault({"x": 10})
print(my_dict["x"])  # Output: 10
print(my_dict["y"])  # Output:
