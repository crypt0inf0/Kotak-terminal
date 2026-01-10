from neo_api_client import NeoAPI
with open('neo_methods.txt', 'w') as f:
    f.write('\n'.join(dir(NeoAPI)))
