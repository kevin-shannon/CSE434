class HashTable:
    def __init__(self, size):
        self.size = size
        self.table = [HashEntry()] * size

    def __repr__(self):
        return str(self.table)

    def hash_func(self, key):
        return sum(bytearray(key, 'utf-8')) % self.size

    def search(self, key, skip_tombstone=True):
        i = self.hash_func(key)
        # Look for an open spot or the key, whichever comes first
        while (self.table[i].record is not None or (self.table[i].tombstone and skip_tombstone)) and self.table[i].key != key:
            i = (i+1) % self.size
            # Key not found or no empty spaces
            if i == self.hash_func(key):
                return None
        return i

    def add(self, record):
        i = self.search(record.data['Long Name'], skip_tombstone=False)
        self.table[i] = HashEntry(record)

    def remove(self, key):
        self.table[self.search(key)] = HashEntry(tombstone=True)

    def lookup(self, key):
        i = self.search(key)
        return self.table[i].record if self.table[i].key == key else None

class HashEntry:
    def __init__(self, record=None, key=None, tombstone=False):
    	self.record = record
    	self.key = record.data['Long Name'] if key is None and record is not None else key
    	self.tombstone = tombstone

    def __repr__(self):
        return repr(self.record)

class Record:
    def __init__(self, data):
        self.data = data

    def __repr__(self):
        return str(self.data)

    def __hash__(self):
        return sum(bytearray(self.data['Long Name'], 'utf-8'))

    def __eq__(self, record):
        return self.data == record.data
