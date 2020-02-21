class HashTable:
    '''
    Custom implementation of a hash table. Uses open indexing with tombstones and
    no resizing functionality.

    Attributes
    ----------
    size : int
        Size of the hash table.
    table : list
        Table contating HashEntries.
    '''

    def __init__(self, size):
        self.size = size
        self.table = [HashEntry()] * size

    def __repr__(self):
        return str(self.table)

    def hash_func(self, key):
        return sum(bytearray(key, 'utf-8')) % self.size

    def search(self, key, skip_tombstone=True):
        '''
        Used by self.add and self.lookup to find the index of a key or the index
        of where a key should go. skip_tombstone is for removing keys so it can
        be sure that the key is not in the hash table.

        Parameters
        ----------
        key : str
            key to be searched for.
        skip_tombstone : bool
            If true, won't stop on an empty entry if it has a tombstone.

        Returns
        -------
        int
            index of key in hash table.
        '''
        i = self.hash_func(key)
        # Look for an open spot or the key, whichever comes first
        while (self.table[i].record is not None or (self.table[i].tombstone and skip_tombstone)) and self.table[i].key != key:
            i = (i+1) % self.size
            # Key not found or no empty spaces
            if i == self.hash_func(key):
                return None
        return i

    def add(self, record):
        '''
        Adds a new entry to the hash table with the record's data.

        Parameters
        ----------
        record : dict
            Dictionary holding a Country's statistics.
        '''
        i = self.search(record['Long Name'], skip_tombstone=False)
        if i is None:
            return
        self.table[i] = HashEntry(record)

    def remove(self, key):
        '''
        Removes an entry from the hash table, leaving a tombstone behind, if
        an entry with the given key is found.

        Parameters
        ----------
        key : str
            key to be removed.
        '''
        i = self.search(key)
        if i is None:
            return
        self.table[i] = HashEntry(tombstone=True)

    def lookup(self, key):
        '''
        Looks up key in hash table.

        Parameters
        ----------
        key : str
            key to lookup.

        Returns
        -------
        dict or None
            If the hash entry is found it will return its record, if not it will return None.
        '''
        i = self.search(key)
        if i is None:
            return
        return self.table[i].record if self.table[i].key == key else None

class HashEntry:
    '''
    Class for each entry in our hash table. Each slot has a potential record,
    key, and tombstone.

    Attributes
    ----------
    record : dict
        value that key is mapping to.
    key : str
        key mapping to this hash entry.
    tombstone : bool
        True if there was once a entry here that got deleted.
    '''

    def __init__(self, record=None, key=None, tombstone=False):
    	self.record = record
    	self.key = record['Long Name'] if key is None and record is not None else key
    	self.tombstone = tombstone

    def __repr__(self):
        return str(self.record)
