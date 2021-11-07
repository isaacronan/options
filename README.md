# options

Investigate options prices and trading scenarios using the E*TRADE API.

## Usage

Build the docker image:

```bash
./build.sh
```

Create a executable shell script called **env.sh** that sets environment variables **ETRADE_KEY** and **ETRADE_SECRET**. For example:

```bash
export ETRADE_KEY='<your api key>'
export ETRADE_SECRET='<your api secret>'
```

Start a jupyter notebook session (which runs on port 8088):

```bash
./jupyter.sh
```

Or enter into a terminal in the docker container to edit/run scripts:

```bash
./run.sh
```