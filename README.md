# Local N8N Development Lab

This repository is a collection of configuration files that define a single `n8n` server running N8N Community Edition and a `Postgres` database. Compiled by Kura Labs, it is intended to faciliate local N8N development and experimentation for learning and instruction purposes.

## Quickstart

> **Prerequisites**
>
> In order to use the lab, you must have, at a minimum, the following installed on your local machine:
> - `git`
> - `docker` and `docker compose`
>
> *Note: To run the lab locally, you should have >=16GB of System Memory on your machine. It may run on machines with less memory, but performance may be poor.*


1. Clone the repo

In your terminal/commandline, navigate to the directory you wish to save the lab files to. Then execute the following to clone the repo to your system:

```bash
git clone <n8n-lab-repository>
cd <n8n-lab-repository>
```

2. Start the services

With the repository downloaded, you can now start up N8N and the other services. In your terminal, execute:

```bash
docker compose up -d
```

This will set up your lab infrastructure. It may take a few minutes to complete depending on your setup.

3. Open the N8N client and register

Once the lab has finished building, you can go ahead and register yourself with the N8N client here:

http://n8n.localhost

That's it! You're ready to get started with creating workflows!


