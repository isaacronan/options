# options

Investigate options prices and trading scenarios using the E*TRADE API.

## Usage

Build the docker image:

```bash
./build.sh
```

Set the environment variables **ETRADE_KEY** and **ETRADE_SECRET**. For example:

```bash
export ETRADE_KEY='<your api key>'
export ETRADE_SECRET='<your api secret>'
```

Start a jupyter notebook session (which runs on port 8088):

```bash
./jupyter.sh
```

Start a server to plot values in a web browser (on port 8000):

```bash
./server.sh
```

Enter into a terminal in the docker container to edit/run scripts:

```bash
./shell.sh
```
