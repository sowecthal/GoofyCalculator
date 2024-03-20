import re

command = 'calc '
command_pattern = r'([a-zA-Z]+)\s(\S+)' 

match = re.match(r'([a-zA-Z]+)\s*(\S+)?', command)
if match:
    groups =  match.groups()
    print(groups)

# match = re.search(command_pattern, command)
# action, args = match.groups()
# print(action, args)

# result = eval(args)
# print(result)