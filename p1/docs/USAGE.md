# Usage
This project is written in python3, make sure to run all processes using python3. To get up and running is fairly simple.

Starting from src/ lets start by making a server process
```
python3 server.py
```
Next lets make a client because our server is getting lonely
```
python3 client.py -i <ip_of_the_server>
```
By Default both client and server will choose port 25565 for communication. This can be changed using the `--port` option.
For more information about the additional arguments of these commands you can use `--help`.

Now that we have a client up and running we can issue some commands to the server.
We want to register a user with user_name 'yang', that will listen on port 25525.
```
register yang 25525
```
The server will store this user and now our client can issue other commands.
You can setup more clients on new terminals or on other nodes similarly.

Once you are happy with the number of clients, setup the DHT.
```
setup-dht <size_of_ring>
```
Whoever issues the command will be the leader of the DHT and other n-1 clients in the ring will be chosen by the server at random.

We now have a DHT, what can you do with a DHT? Query it!
To make sure the querier is free, register a new user before running the following command.
```
query-dht Switzerland
```
If you did everything correctly you should see a record containing more information about Switzerland.

If a user wishes to leave the DHT then they can use
```
leave-dht
```
This will rebuild the dht without them and set there state back to free.

If the user is free then they are allowed to deregister from the server with the following,
```
deregister
```

Finally, if the Leader wishes to completly destroy the DHT they can do so with
```
teardown-dht
```

